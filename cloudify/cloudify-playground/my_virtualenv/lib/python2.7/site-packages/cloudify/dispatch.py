########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


import importlib
import copy
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import StringIO
import Queue
from time import sleep

from cloudify_rest_client.executions import Execution
from cloudify_rest_client.exceptions import InvalidExecutionUpdateStatus

from cloudify import logs
from cloudify import exceptions
from cloudify import state
from cloudify import context
from cloudify import utils
from cloudify import amqp_client_utils
from cloudify import constants
from cloudify.amqp_client_utils import AMQPWrappedThread
from cloudify.manager import update_execution_status, get_rest_client
from cloudify.workflows import workflow_context
from cloudify.workflows import api

CLOUDIFY_DISPATCH = 'CLOUDIFY_DISPATCH'

# This is relevant in integration tests when cloudify-agent is installed in
# editable mode. Adding this directory using PYTHONPATH will make it appear
# after the editable projects appear so it is not applicable in this case.
if os.environ.get('PREPEND_CWD_TO_PYTHONPATH'):
    if os.getcwd() in sys.path:
        sys.path.remove(os.getcwd())
    sys.path.insert(0, os.getcwd())

# Remove different variations in which cloudify may be added to the sys
# path
if os.environ.get(CLOUDIFY_DISPATCH):
    file_dir = os.path.dirname(__file__)
    site_packages_cloudify = os.path.join('site-packages', 'cloudify')
    for entry in copy.copy(sys.path):
        if entry == file_dir or entry.endswith(site_packages_cloudify):
            sys.path.remove(entry)

try:
    from cloudify_agent import VIRTUALENV
    from cloudify_agent.app import app as _app
    task = _app.task(Strategy='cloudify.celery.gate_keeper:GateKeeperStrategy')
except ImportError:
    VIRTUALENV = sys.prefix
    _app = None

    def task(fn):
        return fn


SYSTEM_DEPLOYMENT = '__system__'
PLUGINS_DIR = os.path.join(VIRTUALENV, 'plugins')
DISPATCH_LOGGER_FORMATTER = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s')


class TaskHandler(object):

    def __init__(self, cloudify_context, args, kwargs):
        self.cloudify_context = cloudify_context
        self.args = args
        self.kwargs = kwargs
        self._ctx = None
        self._func = None
        self._zmq_context = None
        self._zmq_socket = None
        self._fallback_handler = None

    def handle_or_dispatch_to_subprocess_if_remote(self):
        if self.cloudify_context.get('task_target'):
            return self.dispatch_to_subprocess()
        else:
            return self.handle()

    def handle(self):
        raise NotImplementedError('Implemented by subclasses')

    def dispatch_to_subprocess(self):
        # inputs.json, output.json and output are written to a temporary
        # directory that only lives during the lifetime of the subprocess
        split = self.cloudify_context['task_name'].split('.')
        dispatch_dir = tempfile.mkdtemp(prefix='task-{0}.{1}-'.format(
            split[0], split[-1]))

        # stdout/stderr are redirected to output. output is only displayed
        # in case something really bad happened. in the general case, output
        # that users want to see in log files, should go through the different
        # loggers
        output = open(os.path.join(dispatch_dir, 'output'), 'w')
        try:
            with open(os.path.join(dispatch_dir, 'input.json'), 'w') as f:
                json.dump({
                    'cloudify_context': self.cloudify_context,
                    'args': self.args,
                    'kwargs': self.kwargs
                }, f)
            env = self._build_subprocess_env()
            command_args = [sys.executable, __file__, dispatch_dir]
            try:
                subprocess.check_call(command_args,
                                      env=env,
                                      bufsize=1,
                                      close_fds=os.name != 'nt',
                                      stdout=output,
                                      stderr=output)
            except subprocess.CalledProcessError:
                # this means something really bad happened because we generally
                # catch all exceptions in the subprocess and exit cleanly
                # regardless.
                output.close()
                with open(os.path.join(dispatch_dir, 'output')) as f:
                    read_output = f.read()
                raise exceptions.NonRecoverableError(
                    'Unhandled exception occurred in operation dispatch: '
                    '{0}'.format(read_output))
            with open(os.path.join(dispatch_dir, 'output.json')) as f:
                dispatch_output = json.load(f)
            if dispatch_output['type'] == 'result':
                return dispatch_output['payload']
            elif dispatch_output['type'] == 'error':
                error = dispatch_output['payload']

                tb = error['traceback']
                exception_type = error['exception_type']
                message = error['message']

                known_exception_type_kwargs = error[
                    'known_exception_type_kwargs']
                causes = known_exception_type_kwargs.pop('causes', [])
                causes.append({
                    'message': message,
                    'type': exception_type,
                    'traceback': tb
                })
                known_exception_type_kwargs['causes'] = causes

                known_exception_type = getattr(exceptions,
                                               error['known_exception_type'])
                known_exception_type_args = error['known_exception_type_args']

                if error['append_message']:
                    known_exception_type_args.append(message)
                else:
                    known_exception_type_args.insert(0, message)
                raise known_exception_type(*known_exception_type_args,
                                           **known_exception_type_kwargs)
            else:
                raise exceptions.NonRecoverableError(
                    'Unexpected output type: {0}'
                    .format(dispatch_output['type']))
        finally:
            output.close()
            shutil.rmtree(dispatch_dir, ignore_errors=True)

    def _build_subprocess_env(self):
        env = os.environ.copy()

        # marker for code that only gets executed when inside the dispatched
        # subprocess, see usage in the imports section of this module
        env[CLOUDIFY_DISPATCH] = 'true'

        # This is used to support environment variables configurations for
        # central deployment based operations. See workflow_context to
        # understand where this value gets set initially
        env.update(self.cloudify_context.get('execution_env') or {})

        # Update PATH environment variable to include bin dir of current
        # virtualenv, and of plugin that includes the operation (if exists)
        bin_dir = 'Scripts' if os.name == 'nt' else 'bin'
        prefixes = [VIRTUALENV]
        plugin_dir = self._extract_plugin_dir()
        if plugin_dir:
            prefixes.insert(0, plugin_dir)
        # Code that concats all bin dirs and is then prepended to the existing
        # PATH environment variable
        task_bin_dirs = [os.path.join(prefix, bin_dir) for prefix in prefixes]
        task_bin_dirs = os.pathsep.join(task_bin_dirs)
        env['PATH'] = '{0}{1}{2}'.format(task_bin_dirs,
                                         os.pathsep,
                                         env.get('PATH', ''))

        # Update PYTHONPATH environment variable to include libraries
        # that belong to plugin running the current operation.
        if plugin_dir:
            if os.name == 'nt':
                plugin_pythonpath_dirs = [os.path.join(
                    plugin_dir, 'Lib', 'site-packages')]
            else:
                # In linux, if plugin has compiled dependencies
                # and was complied for 64bit arch, two libraries should
                # be added: lib and lib64
                plugin_pythonpath_dirs = [os.path.join(
                    plugin_dir, 'lib{0}'.format(b),
                    # e.g. python2.7
                    'python{0}.{1}'.format(sys.version_info[0],
                                           sys.version_info[1]),
                    'site-packages') for b in ['', '64']]
            plugin_pythonpath_dirs = os.pathsep.join(plugin_pythonpath_dirs)
            # Plugin PYTHONPATH is prepended to current PYTHONPATH
            env['PYTHONPATH'] = '{0}{1}{2}'.format(
                plugin_pythonpath_dirs,
                os.pathsep,
                env.get('PYTHONPATH', ''))

        if self.cloudify_context.get('bypass_maintenance'):
            env[constants.BYPASS_MAINTENANCE] = 'True'

        return env

    def _extract_plugin_dir(self):
        plugin = self.cloudify_context.get('plugin', {})
        plugin_name = plugin.get('name')
        package_name = plugin.get('package_name')
        package_version = plugin.get('package_version')
        deployment_id = self.cloudify_context.get('deployment_id',
                                                  SYSTEM_DEPLOYMENT)
        return utils.internal.plugin_prefix(package_name=package_name,
                                            package_version=package_version,
                                            deployment_id=deployment_id,
                                            plugin_name=plugin_name,
                                            sys_prefix_fallback=False)

    def setup_logging(self):
        socket_url = self.cloudify_context.get('socket_url')
        if socket_url:
            import zmq
            self._zmq_context = zmq.Context(io_threads=1)
            self._zmq_socket = self._zmq_context.socket(zmq.PUSH)
            self._zmq_socket.connect(socket_url)
            try:
                handler_context = self.ctx.deployment.id
            except AttributeError:
                handler_context = SYSTEM_DEPLOYMENT
            else:
                # an operation may originate from a system wide workflow.
                # in that case, the deployment id will be None
                handler_context = handler_context or SYSTEM_DEPLOYMENT
            fallback_logger = self._create_fallback_logger(handler_context)
            handler = logs.ZMQLoggingHandler(context=handler_context,
                                             socket=self._zmq_socket,
                                             fallback_logger=fallback_logger)
        else:
            # Used by tests calling dispatch directly with target_name set.
            handler = logging.StreamHandler()
        handler.setFormatter(DISPATCH_LOGGER_FORMATTER)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger()
        logger.handlers = []
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    def _create_fallback_logger(self, handler_context):
        log_dir = None
        if os.environ.get('CELERY_LOG_DIR'):
            log_dir = os.path.join(os.environ['CELERY_LOG_DIR'], 'logs')
        elif os.environ.get('CELERY_WORK_DIR'):
            log_dir = os.environ['CELERY_WORK_DIR']
        if log_dir:
            log_path = os.path.join(log_dir, '{0}.log.fallback'
                                    .format(handler_context))
            fallback_handler = logging.FileHandler(log_path, delay=True)
            self._fallback_handler = fallback_handler
        else:
            # explicitly not setting fallback_handler on self. We don't
            # want to close stderr when the task finishes.
            fallback_handler = logging.StreamHandler()
        fallback_logger = logging.getLogger('dispatch_fallback_logger')
        fallback_handler.setLevel(logging.DEBUG)
        fallback_logger.setLevel(logging.DEBUG)
        fallback_logger.propagate = False
        fallback_logger.handlers = []
        fallback_logger.addHandler(fallback_handler)
        return fallback_logger

    @property
    def ctx_cls(self):
        raise NotImplementedError('implemented by subclasses')

    @property
    def ctx(self):
        if not self._ctx:
            self._ctx = self.ctx_cls(self.cloudify_context)
        return self._ctx

    @property
    def func(self):
        if not self._func:
            task_name = self.cloudify_context['task_name']
            split = task_name.split('.')
            module_name = '.'.join(split[:-1])
            function_name = split[-1]
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                raise exceptions.NonRecoverableError(
                    'No module named {0} ({1})'.format(module_name, e))
            try:
                self._func = getattr(module, function_name)
            except AttributeError:
                raise exceptions.NonRecoverableError(
                    "{0} has no function named '{1}' ".format(module_name,
                                                              function_name))
        return self._func

    def close(self):
        if self._zmq_socket:
            self._zmq_socket.close()
        if self._zmq_context:
            self._zmq_context.term()
        if self._fallback_handler:
            self._fallback_handler.close()


class OperationHandler(TaskHandler):

    @property
    def ctx_cls(self):
        return context.CloudifyContext

    def handle(self):
        if not self.func:
            raise exceptions.NonRecoverableError('func not found: {0}'.
                                                 format(self.cloudify_context))
        ctx = self.ctx
        kwargs = self.kwargs
        if ctx.task_target:
            # # this operation requires an AMQP client
            amqp_client_utils.init_amqp_client()
        else:
            # task is local (not through celery) so we need clone kwarg
            # and an amqp client is not required
            kwargs = copy.deepcopy(kwargs)
        if self.cloudify_context.get('has_intrinsic_functions') is True:
            kwargs = ctx._endpoint.evaluate_functions(payload=kwargs)
        if not self.cloudify_context.get('no_ctx_kwarg'):
            kwargs['ctx'] = ctx
        state.current_ctx.set(ctx, kwargs)
        try:
            result = self.func(*self.args, **kwargs)
        finally:
            amqp_client_utils.close_amqp_client()
            state.current_ctx.clear()
            if ctx.type == context.NODE_INSTANCE:
                ctx.instance.update()
            elif ctx.type == context.RELATIONSHIP_INSTANCE:
                ctx.source.instance.update()
                ctx.target.instance.update()
        if ctx.operation._operation_retry:
            raise ctx.operation._operation_retry
        return result


class WorkflowHandler(TaskHandler):
    @property
    def ctx_cls(self):
        if getattr(self.func, 'workflow_system_wide', False):
            return workflow_context.CloudifySystemWideWorkflowContext
        return workflow_context.CloudifyWorkflowContext

    def handle(self):
        if not self.func:
            raise exceptions.NonRecoverableError(
                'func not found: {0}'.format(self.cloudify_context))

        self.kwargs['ctx'] = self.ctx
        if self.ctx.local:
            return self._handle_local_workflow()
        return self._handle_remote_workflow()

    def _handle_remote_workflow(self):
        rest = get_rest_client()
        amqp_client_utils.init_amqp_client()
        try:
            try:
                self._workflow_started()
            except InvalidExecutionUpdateStatus:
                self._workflow_cancelled()
                return api.EXECUTION_CANCELLED_RESULT

            queue = Queue.Queue()
            t = AMQPWrappedThread(target=self._remote_workflow_child_thread,
                                  args=(queue,),
                                  name='Workflow-Child')
            t.start()

            # while the child thread is executing the workflow, the parent
            # thread is polling for 'cancel' requests while also waiting for
            # messages from the child thread
            result = None
            while True:
                # check if child thread sent a message
                try:
                    data = queue.get(timeout=5)
                    if 'result' in data:
                        # child thread has terminated
                        result = data['result']
                        break
                    else:
                        # error occurred in child thread
                        error = data['error']
                        raise exceptions.ProcessExecutionError(
                            error['message'],
                            error['type'],
                            error['traceback'])
                except Queue.Empty:
                    pass
                # check for 'cancel' requests
                execution = rest.executions.get(self.ctx.execution_id,
                                                _include=['status'])
                if execution.status == Execution.FORCE_CANCELLING:
                    result = api.EXECUTION_CANCELLED_RESULT
                    break
                elif execution.status == Execution.CANCELLING:
                    # send a 'cancel' message to the child thread. It is up to
                    # the workflow implementation to check for this message
                    # and act accordingly (by stopping and raising an
                    # api.ExecutionCancelled error, or by returning the
                    # deprecated api.EXECUTION_CANCELLED_RESULT as result).
                    # parent thread then goes back to polling for messages from
                    # child thread or possibly 'force-cancelling' requests
                    api.cancel_request = True

            if result == api.EXECUTION_CANCELLED_RESULT:
                self._workflow_cancelled()
            else:
                self._workflow_succeeded()
            return result
        except exceptions.ProcessExecutionError as e:
            self._workflow_failed(e, e.traceback)
            raise
        except BaseException as e:
            error = StringIO.StringIO()
            traceback.print_exc(file=error)
            self._workflow_failed(e, error.getvalue())
            raise
        finally:
            amqp_client_utils.close_amqp_client()

    def _remote_workflow_child_thread(self, queue):
        # the actual execution of the workflow will run in another thread.
        # this method is the entry point for that thread, and takes care of
        # forwarding the result or error back to the parent thread
        try:
            self.ctx.internal.start_event_monitor()
            workflow_result = self._execute_workflow_function()
            queue.put({'result': workflow_result})
        except api.ExecutionCancelled:
            queue.put({'result': api.EXECUTION_CANCELLED_RESULT})
        except BaseException as workflow_ex:
            tb = StringIO.StringIO()
            traceback.print_exc(file=tb)
            err = {
                'type': type(workflow_ex).__name__,
                'message': str(workflow_ex),
                'traceback': tb.getvalue()
            }
            queue.put({'error': err})
        finally:
            self.ctx.internal.stop_event_monitor()

    def _handle_local_workflow(self):
        try:
            self._workflow_started()
            result = self._execute_workflow_function()
            self._workflow_succeeded()
            return result
        except Exception, e:
            error = StringIO.StringIO()
            traceback.print_exc(file=error)
            self._workflow_failed(e, error.getvalue())
            raise

    def _execute_workflow_function(self):
        try:
            self.ctx.internal.start_local_tasks_processing()
            state.current_workflow_ctx.set(self.ctx, self.kwargs)
            result = self.func(*self.args, **self.kwargs)
            if not self.ctx.internal.graph_mode:
                tasks = list(self.ctx.internal.task_graph.tasks_iter())
                for workflow_task in tasks:
                    workflow_task.async_result.get()
            return result
        finally:
            self.ctx.internal.stop_local_tasks_processing()
            state.current_workflow_ctx.clear()

    def _workflow_started(self):
        self._update_execution_status(Execution.STARTED)
        self.ctx.internal.send_workflow_event(
            event_type='workflow_started',
            message="Starting '{0}' workflow execution".format(
                self.ctx.workflow_id))

    def _workflow_succeeded(self):
        self._update_execution_status(Execution.TERMINATED)
        self.ctx.internal.send_workflow_event(
            event_type='workflow_succeeded',
            message="'{0}' workflow execution succeeded".format(
                self.ctx.workflow_id))

    def _workflow_failed(self, exception, error_traceback):
        self._update_execution_status(Execution.FAILED, error_traceback)
        self.ctx.internal.send_workflow_event(
            event_type='workflow_failed',
            message="'{0}' workflow execution failed: {1}".format(
                self.ctx.workflow_id, str(exception)),
            args={'error': error_traceback})

    def _workflow_cancelled(self):
        self._update_execution_status(Execution.CANCELLED)
        self.ctx.internal.send_workflow_event(
            event_type='workflow_cancelled',
            message="'{0}' workflow execution cancelled".format(
                self.ctx.workflow_id))

    def _update_execution_status(self, status, error=None):
        if self.ctx.local:
            return
        while True:
            try:
                return update_execution_status(
                    self.ctx.execution_id, status, error)
            except InvalidExecutionUpdateStatus as exc:
                self.ctx.logger.exception(
                    'update execution status is invalid: {0}'.format(exc))
                raise
            except Exception as exc:
                self.ctx.logger.exception(
                    'update execution status got unexpected rest error: {0}'
                    .format(exc))
            sleep(5)


TASK_HANDLERS = {
    'operation': OperationHandler,
    'workflow': WorkflowHandler
}


@task
def dispatch(__cloudify_context, *args, **kwargs):
    dispatch_type = __cloudify_context['type']
    dispatch_handler_cls = TASK_HANDLERS.get(dispatch_type)
    if not dispatch_handler_cls:
        raise exceptions.NonRecoverableError('No handler for task type: {0}'
                                             .format(dispatch_type))
    handler = dispatch_handler_cls(cloudify_context=__cloudify_context,
                                   args=args,
                                   kwargs=kwargs)
    return handler.handle_or_dispatch_to_subprocess_if_remote()


def main():
    dispatch_dir = sys.argv[1]
    with open(os.path.join(dispatch_dir, 'input.json')) as f:
        dispatch_inputs = json.load(f)
    cloudify_context = dispatch_inputs['cloudify_context']
    args = dispatch_inputs['args']
    kwargs = dispatch_inputs['kwargs']
    dispatch_type = cloudify_context['type']
    threading.current_thread().setName('Dispatch-{0}'.format(dispatch_type))
    handler_cls = TASK_HANDLERS[dispatch_type]
    handler = None
    try:
        handler = handler_cls(cloudify_context=cloudify_context,
                              args=args,
                              kwargs=kwargs)
        handler.setup_logging()
        payload = handler.handle()
        payload_type = 'result'
    except BaseException as e:

        tb = StringIO.StringIO()
        traceback.print_exc(file=tb)
        trace_out = tb.getvalue()

        # Needed because HttpException constructor sucks
        append_message = False
        # Convert exception to a know exception type that can be deserialized
        # by the calling process
        known_exception_type_args = []
        if isinstance(e, exceptions.ProcessExecutionError):
            known_exception_type = exceptions.ProcessExecutionError
            known_exception_type_args = [e.error_type, e.traceback]
            trace_out = e.traceback
        elif isinstance(e, exceptions.HttpException):
            known_exception_type = exceptions.HttpException
            known_exception_type_args = [e.url, e.code]
            append_message = True
        elif isinstance(e, exceptions.NonRecoverableError):
            known_exception_type = exceptions.NonRecoverableError
        elif isinstance(e, exceptions.OperationRetry):
            known_exception_type = exceptions.OperationRetry
            known_exception_type_args = [e.retry_after]
        elif isinstance(e, exceptions.RecoverableError):
            known_exception_type = exceptions.RecoverableError
            known_exception_type_args = [e.retry_after]
        else:
            # convert pure user exceptions to a RecoverableError
            known_exception_type = exceptions.RecoverableError

        try:
            causes = e.causes
        except AttributeError:
            causes = []

        payload_type = 'error'
        payload = {
            'traceback': trace_out,
            'exception_type': type(e).__name__,
            'message': str(e),
            'known_exception_type': known_exception_type.__name__,
            'known_exception_type_args': known_exception_type_args,
            'known_exception_type_kwargs': {'causes': causes or []},
            'append_message': append_message,
        }

        logger = logging.getLogger(__name__)
        logger.error('Task {0}[{1}] raised:\n{2}'.format(
            handler.cloudify_context['task_name'],
            handler.cloudify_context.get('task_id', '<no-id>'),
            trace_out))

    finally:
        if handler:
            handler.close()
    with open(os.path.join(dispatch_dir, 'output.json'), 'w') as f:
        json.dump({
            'type': payload_type,
            'payload': payload
        }, f)


if __name__ == '__main__':
    main()
