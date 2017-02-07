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

"""
Handles 'cfy dev'
"""

from fabric.api import env
from cloudify_cli import utils
from cloudify_cli import exec_env
from fabric.context_managers import settings
from cloudify_cli.utils import get_management_key
from cloudify_cli.utils import get_management_user
from cloudify_cli.exceptions import CloudifyCliError


def dev(args, task, tasks_file):
    management_ip = utils.get_management_server_ip()
    _execute(username=get_management_user(),
             key=get_management_key(),
             ip=management_ip,
             task=task,
             tasks_file=tasks_file,
             args=args)


def _execute(username, key, ip, task, tasks_file, args):
    _setup_fabric_env(username=username,
                      key=key)
    tasks = exec_tasks_file(tasks_file=tasks_file)
    _execute_task(ip=ip,
                  task=task,
                  tasks=tasks,
                  task_args=args)


def _setup_fabric_env(username, key):
    env.user = username
    env.key_filename = key
    env.warn_only = True
    env.abort_on_prompts = False
    env.connection_attempts = 5
    env.keepalive = 0
    env.linewise = False
    env.pool_size = 0
    env.skip_bad_hosts = False
    env.timeout = 10
    env.forward_agent = True
    env.status = False
    env.disable_known_hosts = False


def exec_tasks_file(tasks_file=None):
    tasks_file = tasks_file or 'tasks.py'
    exec_globals = exec_env.exec_globals(tasks_file)
    try:
        execfile(tasks_file, exec_globals)
    except Exception as e:
        raise CloudifyCliError('Failed evaluating {0} ({1}:{2}'
                               .format(tasks_file, type(e).__name__, e))

    return dict([(task_name, task) for task_name, task in exec_globals.items()
                 if callable(task) and not task_name.startswith('_')])


def _execute_task(ip, task, tasks, task_args):
    task = task.replace('-', '_')
    args, kwargs = _parse_task_args(task_args)
    task_function = tasks.get(task)
    if not task_function:
        raise CloudifyCliError('Task {0} not found'.format(task))
    try:
        with settings(host_string=ip):
            task_function(*args, **kwargs)
    except Exception as e:
        raise CloudifyCliError('Failed to execute {0} ({1}) '.format(
            task, str(e)))


def _parse_task_args(task_args):
    task_args = task_args or []
    args = []
    kwargs = {}
    for task_arg in task_args:
        if task_arg.startswith('--'):
            task_arg = task_arg[2:]
            split = task_arg.split('=')
            key = split[0].replace('-', '_')
            if len(split) == 1:
                if key.startswith('no_'):
                    key = key[3:]
                    value = False
                else:
                    value = True
            else:
                value = ''.join(split[1:])
            kwargs[key] = value
        else:
            args.append(task_arg)
    return args, kwargs
