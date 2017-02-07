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


import json
import subprocess
import os
import sys
import time
import threading
from StringIO import StringIO
import tempfile

import requests

from cloudify import ctx as operation_ctx
from cloudify.workflows import ctx as workflows_ctx
from cloudify.decorators import operation, workflow
from cloudify.exceptions import NonRecoverableError

from script_runner import eval_env
from cloudify.proxy.client import CTX_SOCKET_URL


from cloudify.proxy.server import (UnixCtxProxy,
                                   TCPCtxProxy,
                                   HTTPCtxProxy,
                                   StubCtxProxy)

try:
    import zmq  # noqa
    HAS_ZMQ = True
except ImportError:
    HAS_ZMQ = False

try:
    from cloudify.proxy.client import ScriptException
except ImportError:
    ScriptException = None


ILLEGAL_CTX_OPERATION_ERROR = RuntimeError('ctx may only abort or return once')
UNSUPPORTED_SCRIPT_FEATURE_ERROR = \
    RuntimeError('ctx abort & retry commands are only supported in Cloudify '
                 '3.4 or later')

IS_WINDOWS = os.name == 'nt'


@operation
def run(script_path, process=None, **kwargs):
    ctx = operation_ctx._get_current_object()
    if script_path is None:
        raise NonRecoverableError('Script path parameter not defined')
    process = create_process_config(process or {}, kwargs)
    script_path = download_resource(ctx.download_resource, script_path)
    os.chmod(script_path, 0755)
    script_func = get_run_script_func(script_path, process)
    return process_execution(script_func, script_path, ctx, process)


@workflow
def execute_workflow(script_path, **kwargs):
    ctx = workflows_ctx._get_current_object()
    script_path = download_resource(
        ctx.internal.handler.download_blueprint_resource, script_path)
    return process_execution(eval_script, script_path, ctx)


def create_process_config(process, operation_kwargs):
    env_vars = operation_kwargs.copy()
    if 'ctx' in env_vars:
        del env_vars['ctx']
    env_vars.update(process.get('env', {}))
    output_env_vars = {}
    for k, v in env_vars.items():
        k = str(k)
        if isinstance(v, (dict, list, set, bool)):
            output_env_vars[k] = json.dumps(v)
        else:
            output_env_vars[k] = str(v)
    process['env'] = output_env_vars
    return process


def process_execution(script_func, script_path, ctx, process=None):

    ctx.is_script_exception_defined = ScriptException is not None

    def abort_operation(message=None):
        if ctx._return_value is not None:
            ctx._return_value = ILLEGAL_CTX_OPERATION_ERROR
            raise ctx._return_value
        if ctx.is_script_exception_defined:
            ctx._return_value = ScriptException(message)
        else:
            ctx._return_value = UNSUPPORTED_SCRIPT_FEATURE_ERROR
            raise ctx._return_value
        return ctx._return_value

    def retry_operation(message=None, retry_after=None):
        if ctx._return_value is not None:
            ctx._return_value = ILLEGAL_CTX_OPERATION_ERROR
            raise ctx._return_value
        if ctx.is_script_exception_defined:
            ctx._return_value = ScriptException(message, retry=True)
            ctx.operation.retry(message=message, retry_after=retry_after)
        else:
            ctx._return_value = UNSUPPORTED_SCRIPT_FEATURE_ERROR
            raise ctx._return_value
        return ctx._return_value

    ctx.abort_operation = abort_operation
    ctx.retry_operation = retry_operation

    def returns(value):
        if ctx._return_value is not None:
            ctx._return_value = ILLEGAL_CTX_OPERATION_ERROR
            raise ctx._return_value
        ctx._return_value = value
    ctx.returns = returns

    ctx._return_value = None

    script_func(script_path, ctx, process)
    script_result = ctx._return_value
    if (ctx.is_script_exception_defined and
       isinstance(script_result, ScriptException)):
        if script_result.retry:
            return script_result
        else:
            raise NonRecoverableError(str(script_result))
    else:
        return script_result


def get_run_script_func(script_path, process):
    eval_python = process.get('eval_python')
    if eval_python is True or (script_path.endswith('.py') and
                               eval_python is not False):
        return eval_script
    else:
        return execute


def execute(script_path, ctx, process):
    on_posix = 'posix' in sys.builtin_module_names

    proxy = start_ctx_proxy(ctx, process)

    env = os.environ.copy()
    process_env = process.get('env', {})
    env.update(process_env)
    env[CTX_SOCKET_URL] = proxy.socket_url

    cwd = process.get('cwd')

    command_prefix = process.get('command_prefix')
    if command_prefix:
        command = '{0} {1}'.format(command_prefix, script_path)
    else:
        command = script_path

    args = process.get('args')
    if args:
        command = ' '.join([command] + args)

    ctx.logger.info('Executing: {0}'.format(command))

    process = subprocess.Popen(command,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               env=env,
                               cwd=cwd,
                               bufsize=1,
                               close_fds=on_posix)

    return_code = None

    stdout_consumer = OutputConsumer(process.stdout)
    stderr_consumer = OutputConsumer(process.stderr)

    while True:
        process_ctx_request(proxy)
        return_code = process.poll()
        if return_code is not None:
            break
        time.sleep(0.1)

    proxy.close()
    stdout_consumer.join()
    stderr_consumer.join()

    ctx.logger.info('Execution done (return_code={0}): {1}'
                    .format(return_code, command))

    # happens when more than 1 ctx result command is used
    if isinstance(ctx._return_value, RuntimeError):
        raise NonRecoverableError(str(ctx._return_value))
    elif return_code != 0:
        if not (ctx.is_script_exception_defined and
           isinstance(ctx._return_value, ScriptException)):
                raise ProcessException(command,
                                       return_code,
                                       stdout_consumer.buffer.getvalue(),
                                       stderr_consumer.buffer.getvalue())


def start_ctx_proxy(ctx, process):
    ctx_proxy_type = process.get('ctx_proxy_type')
    if not ctx_proxy_type or ctx_proxy_type == 'auto':
        if HAS_ZMQ:
            if IS_WINDOWS:
                return TCPCtxProxy(ctx)
            else:
                return UnixCtxProxy(ctx)
        else:
            return HTTPCtxProxy(ctx)
    elif ctx_proxy_type == 'unix':
        return UnixCtxProxy(ctx)
    elif ctx_proxy_type == 'tcp':
        return TCPCtxProxy(ctx)
    elif ctx_proxy_type == 'http':
        return HTTPCtxProxy(ctx)
    elif ctx_proxy_type == 'none':
        return StubCtxProxy()
    else:
        raise NonRecoverableError('Unsupported proxy type: {0}'
                                  .format(ctx_proxy_type))


def process_ctx_request(proxy):
    if isinstance(proxy, StubCtxProxy):
        return
    if isinstance(proxy, HTTPCtxProxy):
        return
    proxy.poll_and_process(timeout=0)


def eval_script(script_path, ctx, process=None):
    eval_globals = eval_env.setup_env_and_globals(script_path)
    execfile(script_path, eval_globals)


def download_resource(download_resource_func, script_path):
    split = script_path.split('://')
    schema = split[0]
    if schema in ['http', 'https']:
        response = requests.get(script_path)
        if response.status_code == 404:
            raise NonRecoverableError('Failed downloading script: {0} ('
                                      'status code: {1})'
                                      .format(script_path,
                                              response.status_code))
        content = response.text
        suffix = script_path.split('/')[-1]
        script_path = tempfile.mktemp(suffix='-{0}'.format(suffix))
        with open(script_path, 'w') as f:
            f.write(content)
        return script_path
    else:
        return download_resource_func(script_path)


class OutputConsumer(object):

    def __init__(self, out):
        self.out = out
        self.buffer = StringIO()
        self.consumer = threading.Thread(target=self.consume_output)
        self.consumer.daemon = True
        self.consumer.start()

    def consume_output(self):
        for line in iter(self.out.readline, b''):
            self.buffer.write(line)
        self.out.close()

    def join(self):
        self.consumer.join()


class ProcessException(Exception):

    def __init__(self, command, exit_code, stdout, stderr):
        super(ProcessException, self).__init__(stderr)
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
