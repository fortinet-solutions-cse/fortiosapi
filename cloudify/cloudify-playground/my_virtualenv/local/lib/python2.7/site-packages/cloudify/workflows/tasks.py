########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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


import sys
import time
import uuid
import Queue

from cloudify import utils
from cloudify import exceptions
from cloudify.workflows import api

INFINITE_TOTAL_RETRIES = -1
DEFAULT_TOTAL_RETRIES = INFINITE_TOTAL_RETRIES
DEFAULT_RETRY_INTERVAL = 30
DEFAULT_SUBGRAPH_TOTAL_RETRIES = 0

DEFAULT_SEND_TASK_EVENTS = True

TASK_PENDING = 'pending'
TASK_SENDING = 'sending'
TASK_SENT = 'sent'
TASK_STARTED = 'started'
TASK_RESCHEDULED = 'rescheduled'
TASK_SUCCEEDED = 'succeeded'
TASK_FAILED = 'failed'

TERMINATED_STATES = [TASK_RESCHEDULED, TASK_SUCCEEDED, TASK_FAILED]

DISPATCH_TASK = 'cloudify.dispatch.dispatch'

INSPECT_TIMEOUT = 30


def retry_failure_handler(task):
    """Basic on_success/on_failure handler that always returns retry"""
    return HandlerResult.retry()


class WorkflowTask(object):
    """A base class for workflow tasks"""

    def __init__(self,
                 workflow_context,
                 task_id=None,
                 info=None,
                 on_success=None,
                 on_failure=None,
                 total_retries=DEFAULT_TOTAL_RETRIES,
                 retry_interval=DEFAULT_RETRY_INTERVAL,
                 send_task_events=DEFAULT_SEND_TASK_EVENTS):
        """
        :param task_id: The id of this task (generated if none is provided)
        :param info: A short description of this task (for logging)
        :param on_success: A handler called when the task's execution
                           terminates successfully.
                           Expected to return one of
                           [HandlerResult.retry(), HandlerResult.cont()]
                           to indicate whether this task should be re-executed.
        :param on_failure: A handler called when the task's execution
                           fails.
                           Expected to return one of
                           [HandlerResult.retry(), HandlerResult.ignore(),
                            HandlerResult.fail()]
                           to indicate whether this task should be re-executed,
                           cause the engine to terminate workflow execution
                           immediately or simply ignore this task failure and
                           move on.
        :param total_retries: Maximum retry attempt for this task, in case
                              the handlers return a retry attempt.
        :param retry_interval: Number of seconds to wait between retries
        :param workflow_context: the CloudifyWorkflowContext instance
        """
        self.id = task_id or str(uuid.uuid4())
        self._state = TASK_PENDING
        self.async_result = None
        self.on_success = on_success
        self.on_failure = on_failure
        self.info = info
        self.error = None
        self.total_retries = total_retries
        self.retry_interval = retry_interval
        self.terminated = Queue.Queue(maxsize=1)
        self.is_terminated = False
        self.workflow_context = workflow_context
        self.send_task_events = send_task_events
        self.containing_subgraph = None

        self.current_retries = 0
        # timestamp for which the task should not be executed
        # by the task graph before reached, overridden by the task
        # graph during retries
        self.execute_after = time.time()

    def dump(self):
        return {
            'id': self.id,
            'state': self.get_state(),
            'info': self.info,
            'error': self.error,
            'current_retries': self.current_retries,
            'cloudify_context': self.cloudify_context
        }

    def is_remote(self):
        """
        :return: Is this a remote task
        """
        return not self.is_local()

    def is_local(self):
        """
        :return: Is this a local task
        """
        raise NotImplementedError('Implemented by subclasses')

    def is_nop(self):
        """
        :return: Is this a NOP task
        """
        return False

    def get_state(self):
        """
        Get the task state

        :return: The task state [pending, sending, sent, started,
                                 rescheduled, succeeded, failed]
        """
        return self._state

    def set_state(self, state):
        """
        Set the task state

        :param state: The state to set [pending, sending, sent, started,
                                        rescheduled, succeeded, failed]
        """
        if state not in [TASK_PENDING, TASK_SENDING, TASK_SENT, TASK_STARTED,
                         TASK_RESCHEDULED, TASK_SUCCEEDED, TASK_FAILED]:
            raise RuntimeError('Illegal state set on task: {0} '
                               '[task={1}]'.format(state, str(self)))
        self._state = state
        if state in TERMINATED_STATES:
            self.is_terminated = True
            self.terminated.put_nowait(True)

    def wait_for_terminated(self, timeout=None):
        if self.is_terminated:
            return
        self.terminated.get(timeout=timeout)

    def handle_task_terminated(self):
        if self.get_state() in (TASK_FAILED, TASK_RESCHEDULED):
            handler_result = self._handle_task_not_succeeded()
        else:
            handler_result = self._handle_task_succeeded()

        if handler_result.action == HandlerResult.HANDLER_RETRY:
            if any([self.total_retries == INFINITE_TOTAL_RETRIES,
                    self.current_retries < self.total_retries,
                    handler_result.ignore_total_retries]):
                if handler_result.retry_after is None:
                    handler_result.retry_after = self.retry_interval
                if handler_result.retried_task is None:
                    new_task = self.duplicate_for_retry(
                        time.time() + handler_result.retry_after)
                    handler_result.retried_task = new_task
            else:
                handler_result.action = HandlerResult.HANDLER_FAIL

        if self.containing_subgraph:
            subgraph = self.containing_subgraph
            retried_task = None
            if handler_result.action == HandlerResult.HANDLER_FAIL:
                handler_result.action = HandlerResult.HANDLER_IGNORE
                # It is possible that two concurrent tasks failed.
                # we will only consider the first one handled
                if not subgraph.failed_task:
                    subgraph.failed_task = self
                    subgraph.set_state(TASK_FAILED)
            elif handler_result.action == HandlerResult.HANDLER_RETRY:
                retried_task = handler_result.retried_task
            subgraph.task_terminated(task=self, new_task=retried_task)

        return handler_result

    def _handle_task_succeeded(self):
        """Call handler for task success"""
        if self.on_success:
            return self.on_success(self)
        else:
            return HandlerResult.cont()

    def _handle_task_not_succeeded(self):

        """
        Call handler for task which hasn't ended in 'succeeded' state
        (i.e. has either failed or been rescheduled)
        """

        try:
            exception = self.async_result.result
        except Exception as e:
            exception = exceptions.NonRecoverableError(
                'Could not de-serialize '
                'exception of task {0} --> {1}: {2}'
                .format(self.name,
                        type(e).__name__,
                        str(e)))

        if isinstance(exception, exceptions.OperationRetry):
            # operation explicitly requested a retry, so we ignore
            # the handler set on the task.
            handler_result = HandlerResult.retry()
        elif self.on_failure:
            handler_result = self.on_failure(self)
        else:
            handler_result = HandlerResult.retry()

        if handler_result.action == HandlerResult.HANDLER_RETRY:
            if isinstance(exception, exceptions.NonRecoverableError):
                handler_result = HandlerResult.fail()
            elif isinstance(exception, exceptions.RecoverableError):
                handler_result.retry_after = exception.retry_after

        if not self.is_subgraph:
            causes = []
            if isinstance(exception, (exceptions.RecoverableError,
                                      exceptions.NonRecoverableError)):
                causes = exception.causes
            if isinstance(self, LocalWorkflowTask):
                tb = self.async_result._holder.error[1]
                causes.append(utils.exception_to_error_cause(exception, tb))
            self.workflow_context.internal.send_task_event(
                state=self.get_state(),
                task=self,
                event={'exception': exception, 'causes': causes})

        return handler_result

    def __str__(self):
        suffix = self.info if self.info is not None else ''
        return '{0}({1})'.format(self.name, suffix)

    def duplicate_for_retry(self, execute_after):
        """
        :return: A new instance of this task with a new task id
        """
        dup = self._duplicate()
        dup.execute_after = execute_after
        dup.current_retries = self.current_retries + 1
        if dup.cloudify_context and 'operation' in dup.cloudify_context:
            op_ctx = dup.cloudify_context['operation']
            op_ctx['retry_number'] = dup.current_retries
        return dup

    def _duplicate(self):
        raise NotImplementedError('Implemented by subclasses')

    @property
    def cloudify_context(self):
        raise NotImplementedError('Implemented by subclasses')

    @property
    def name(self):
        """
        :return: The task name
        """

        raise NotImplementedError('Implemented by subclasses')

    @property
    def is_subgraph(self):
        return False


class RemoteWorkflowTask(WorkflowTask):
    """A WorkflowTask wrapping a celery based task"""

    # cache for registered tasks queries to celery workers
    cache = {}

    def __init__(self,
                 kwargs,
                 cloudify_context,
                 workflow_context,
                 task_queue=None,
                 task_target=None,
                 task_id=None,
                 info=None,
                 on_success=None,
                 on_failure=retry_failure_handler,
                 total_retries=DEFAULT_TOTAL_RETRIES,
                 retry_interval=DEFAULT_RETRY_INTERVAL,
                 send_task_events=DEFAULT_SEND_TASK_EVENTS):
        """
        :param kwargs: The keyword argument this task will be invoked with
        :param cloudify_context: the cloudify context dict
        :param task_queue: the cloudify context dict
        :param task_target: the cloudify context dict
        :param task_id: The id of this task (generated if none is provided)
        :param info: A short description of this task (for logging)
        :param on_success: A handler called when the task's execution
                           terminates successfully.
                           Expected to return one of
                           [HandlerResult.retry(), HandlerResult.cont()]
                           to indicate whether this task should be re-executed.
        :param on_failure: A handler called when the task's execution
                           fails.
                           Expected to return one of
                           [HandlerResult.retry(), HandlerResult.ignore(),
                            HandlerResult.fail()]
                           to indicate whether this task should be re-executed,
                           cause the engine to terminate workflow execution
                           immediately or simply ignore this task failure and
                           move on.
        :param total_retries: Maximum retry attempt for this task, in case
                              the handlers return a retry attempt.
        :param retry_interval: Number of seconds to wait between retries
        :param workflow_context: the CloudifyWorkflowContext instance
        """
        super(RemoteWorkflowTask, self).__init__(
            workflow_context,
            task_id,
            info=info,
            on_success=on_success,
            on_failure=on_failure,
            total_retries=total_retries,
            retry_interval=retry_interval,
            send_task_events=send_task_events)
        self._task_target = task_target
        self._task_queue = task_queue
        self._kwargs = kwargs
        self._cloudify_context = cloudify_context

    def apply_async(self):
        """
        Call the underlying celery tasks apply_async. Verify the worker
        is alive and send an event before doing so.

        :return: a RemoteWorkflowTaskResult instance wrapping the
                 celery async result
        """
        try:
            task, self._task_queue, self._task_target = \
                self.workflow_context.internal.handler.get_task(
                    self, queue=self._task_queue, target=self._task_target)
            self._verify_worker_alive()
            self.workflow_context.internal.send_task_event(TASK_SENDING, self)
            self.set_state(TASK_SENT)
            async_result = task.apply_async(task_id=self.id)
            self.async_result = RemoteWorkflowTaskResult(self, async_result)
        except (exceptions.NonRecoverableError,
                exceptions.RecoverableError) as e:
            self.set_state(TASK_FAILED)
            self.async_result = RemoteWorkflowErrorTaskResult(self, e)
        return self.async_result

    def is_local(self):
        return False

    def _duplicate(self):
        dup = RemoteWorkflowTask(kwargs=self._kwargs,
                                 task_queue=self.queue,
                                 task_target=self.target,
                                 cloudify_context=self.cloudify_context,
                                 workflow_context=self.workflow_context,
                                 task_id=None,  # we want a new task id
                                 info=self.info,
                                 on_success=self.on_success,
                                 on_failure=self.on_failure,
                                 total_retries=self.total_retries,
                                 retry_interval=self.retry_interval,
                                 send_task_events=self.send_task_events)
        dup.cloudify_context['task_id'] = dup.id
        return dup

    @property
    def name(self):
        """The task name"""
        return self.cloudify_context['task_name']

    @property
    def cloudify_context(self):
        return self._cloudify_context

    @property
    def target(self):
        """The task target (worker name)"""
        return self._task_target

    @property
    def queue(self):
        """The task queue"""
        return self._task_queue

    @property
    def kwargs(self):
        """kwargs to pass when invoking the task"""
        return self._kwargs

    def _verify_worker_alive(self):
        verify_worker_alive(self.name,
                            self.target,
                            self._get_registered)

    def _get_registered(self):
        # import here because this only applies in remote execution
        # environments
        from cloudify_agent.app import app

        worker_name = 'celery@{0}'.format(self.target)
        inspect = app.control.inspect(destination=[worker_name],
                                      timeout=INSPECT_TIMEOUT)
        registered = inspect.registered()
        if registered is None or worker_name not in registered:
            return None
        return set(registered[worker_name])


class LocalWorkflowTask(WorkflowTask):
    """A WorkflowTask wrapping a local callable"""

    def __init__(self,
                 local_task,
                 workflow_context,
                 node=None,
                 info=None,
                 on_success=None,
                 on_failure=retry_failure_handler,
                 total_retries=DEFAULT_TOTAL_RETRIES,
                 retry_interval=DEFAULT_RETRY_INTERVAL,
                 send_task_events=DEFAULT_SEND_TASK_EVENTS,
                 kwargs=None,
                 task_id=None,
                 name=None):
        """
        :param local_task: A callable
        :param workflow_context: the CloudifyWorkflowContext instance
        :param node: The CloudifyWorkflowNode instance (if in node context)
        :param info: A short description of this task (for logging)
        :param on_success: A handler called when the task's execution
                           terminates successfully.
                           Expected to return one of
                           [HandlerResult.retry(), HandlerResult.cont()]
                           to indicate whether this task should be re-executed.
        :param on_failure: A handler called when the task's execution
                           fails.
                           Expected to return one of
                           [HandlerResult.retry(), HandlerResult.ignore(),
                            HandlerResult.fail()]
                           to indicate whether this task should be re-executed,
                           cause the engine to terminate workflow execution
                           immediately or simply ignore this task failure and
                           move on.
        :param total_retries: Maximum retry attempt for this task, in case
                              the handlers return a retry attempt.
        :param retry_interval: Number of seconds to wait between retries
        :param kwargs: Local task keyword arguments
        :param name: optional parameter (default: local_task.__name__)
        """
        super(LocalWorkflowTask, self).__init__(
            info=info,
            on_success=on_success,
            on_failure=on_failure,
            total_retries=total_retries,
            retry_interval=retry_interval,
            task_id=task_id,
            workflow_context=workflow_context,
            send_task_events=send_task_events)
        self.local_task = local_task
        self.node = node
        self.kwargs = kwargs or {}
        self._name = name or local_task.__name__

    def dump(self):
        super_dump = super(LocalWorkflowTask, self).dump()
        super_dump.update({
            'name': self._name
        })
        return super_dump

    def apply_async(self):
        """
        Execute the task in the local task thread pool
        :return: A wrapper for the task result
        """

        def local_task_wrapper():
            try:
                self.workflow_context.internal.send_task_event(TASK_STARTED,
                                                               self)
                result = self.local_task(**self.kwargs)
                self.workflow_context.internal.send_task_event(
                    TASK_SUCCEEDED, self, event={'result': str(result)})
                self.async_result._holder.result = result
                self.set_state(TASK_SUCCEEDED)
            except BaseException as e:
                new_task_state = TASK_RESCHEDULED if isinstance(
                    e, exceptions.OperationRetry) else TASK_FAILED
                exc_type, exception, tb = sys.exc_info()
                self.async_result._holder.error = (exception, tb)
                self.set_state(new_task_state)

        self.async_result = LocalWorkflowTaskResult(self)

        self.workflow_context.internal.send_task_event(TASK_SENDING, self)
        self.set_state(TASK_SENT)
        self.workflow_context.internal.add_local_task(local_task_wrapper)

        return self.async_result

    def is_local(self):
        return True

    def _duplicate(self):
        dup = LocalWorkflowTask(local_task=self.local_task,
                                workflow_context=self.workflow_context,
                                node=self.node,
                                info=self.info,
                                on_success=self.on_success,
                                on_failure=self.on_failure,
                                total_retries=self.total_retries,
                                retry_interval=self.retry_interval,
                                send_task_events=self.send_task_events,
                                kwargs=self.kwargs,
                                name=self.name)
        return dup

    @property
    def name(self):
        """The task name"""
        return self._name

    @property
    def cloudify_context(self):
        return self.kwargs.get('__cloudify_context')


# NOP tasks class
class NOPLocalWorkflowTask(LocalWorkflowTask):

    def __init__(self, workflow_context):
        super(NOPLocalWorkflowTask, self).__init__(lambda: None,
                                                   workflow_context)

    @property
    def name(self):
        """The task name"""
        return 'NOP'

    def apply_async(self):
        self.set_state(TASK_SUCCEEDED)
        return LocalWorkflowTaskResult(self)

    def is_nop(self):
        return True


class WorkflowTaskResult(object):
    """A base wrapper for workflow task results"""

    def __init__(self, task):
        self.task = task

    def _process(self, retry_on_failure):
        if self.task.workflow_context.internal.graph_mode:
            return self._get()
        task_graph = self.task.workflow_context.internal.task_graph
        while True:
            self._wait_for_task_terminated()
            handler_result = self.task.handle_task_terminated()
            task_graph.remove_task(self.task)
            try:
                result = self._get()
                if handler_result.action != HandlerResult.HANDLER_RETRY:
                    return result
            except:
                if (not retry_on_failure or
                        handler_result.action == HandlerResult.HANDLER_FAIL):
                    raise
            self._sleep(handler_result.retry_after)
            self.task = handler_result.retried_task
            task_graph.add_task(self.task)
            self._check_execution_cancelled()
            self.task.apply_async()
            self._refresh_state()

    @staticmethod
    def _check_execution_cancelled():
        if api.has_cancel_request():
            raise api.ExecutionCancelled()

    def _wait_for_task_terminated(self):
        while True:
            self._check_execution_cancelled()
            try:
                self.task.wait_for_terminated(timeout=1)
                break
            except Queue.Empty:
                continue

    def _sleep(self, seconds):
        while seconds > 0:
            self._check_execution_cancelled()
            sleep_time = 1 if seconds > 1 else seconds
            time.sleep(sleep_time)
            seconds -= sleep_time

    def get(self, retry_on_failure=True):
        """
        Get the task result.
        Will block until the task execution ends.

        :return: The task result
        """
        return self._process(retry_on_failure)

    def _get(self):
        raise NotImplementedError('Implemented by subclasses')

    def _refresh_state(self):
        raise NotImplementedError('Implemented by subclasses')


class RemoteWorkflowErrorTaskResult(WorkflowTaskResult):

    def __init__(self, task, exception):
        super(RemoteWorkflowErrorTaskResult, self).__init__(task)
        self.exception = exception

    def _get(self):
        raise self.exception

    @property
    def result(self):
        return self.exception


class RemoteWorkflowTaskResult(WorkflowTaskResult):
    """A wrapper for celery's AsyncResult"""

    def __init__(self, task, async_result):
        super(RemoteWorkflowTaskResult, self).__init__(task)
        self.async_result = async_result

    def _get(self):
        return self.async_result.get()

    def _refresh_state(self):
        self.async_result = self.task.async_result.async_result

    @property
    def result(self):
        return self.async_result.result


class LocalWorkflowTaskResult(WorkflowTaskResult):
    """A wrapper for local workflow task results"""

    class ResultHolder(object):

        def __init__(self, result=None, error=None):
            self.result = result
            self.error = error

    def __init__(self, task):
        """
        :param task: The LocalWorkflowTask instance
        """
        super(LocalWorkflowTaskResult, self).__init__(task)
        self._holder = self.ResultHolder()

    def _get(self):
        if self._holder.error is not None:
            exception, traceback = self._holder.error
            raise exception, None, traceback
        return self._holder.result

    def _refresh_state(self):
        self._holder = self.task.async_result._holder

    @property
    def result(self):
        if self._holder.error:
            return self._holder.error[0]
        else:
            return self._holder.result


class StubAsyncResult(object):
    """Stub async result that always returns None"""
    result = None


class HandlerResult(object):

    HANDLER_RETRY = 'handler_retry'
    HANDLER_FAIL = 'handler_fail'
    HANDLER_IGNORE = 'handler_ignore'
    HANDLER_CONTINUE = 'handler_continue'

    def __init__(self,
                 action,
                 ignore_total_retries=False,
                 retry_after=None):
        self.action = action
        self.ignore_total_retries = ignore_total_retries
        self.retry_after = retry_after

        # this field is filled by handle_terminated_task() below after
        # duplicating the task and updating the relevant task fields
        # or by a subgraph on_XXX handler
        self.retried_task = None

    @classmethod
    def retry(cls, ignore_total_retries=False, retry_after=None):
        return HandlerResult(cls.HANDLER_RETRY,
                             ignore_total_retries=ignore_total_retries,
                             retry_after=retry_after)

    @classmethod
    def fail(cls):
        return HandlerResult(cls.HANDLER_FAIL)

    @classmethod
    def cont(cls):
        return HandlerResult(cls.HANDLER_CONTINUE)

    @classmethod
    def ignore(cls):
        return HandlerResult(cls.HANDLER_IGNORE)


def verify_worker_alive(name, target, get_registered):

    cache = RemoteWorkflowTask.cache
    registered = cache.get(target)
    if not registered:
        registered = get_registered()
        cache[target] = registered

    if registered is None:
        raise exceptions.RecoverableError(
            'Timed out querying worker celery@{0} for its registered '
            'tasks. [timeout={1} seconds]'.format(target, INSPECT_TIMEOUT))

    if DISPATCH_TASK not in registered:
        raise exceptions.NonRecoverableError(
            'Missing {0} task in worker {1} \n'
            'Registered tasks are: {2}. (This probably means the agent '
            'configuration is invalid) [{3}]'.format(
                DISPATCH_TASK, target, registered, name))
