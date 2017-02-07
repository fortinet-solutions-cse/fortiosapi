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


from cloudify import logs
from cloudify.exceptions import OperationRetry
from cloudify.workflows import tasks as tasks_api


class Monitor(object):
    """Monitor with handlers for different celery events"""

    def __init__(self, tasks_graph):
        """
        :param tasks_graph: The task graph. Used to extract tasks based on the
                            events task id.
        """
        self.tasks_graph = tasks_graph
        self._receiver = None
        self._should_stop = False

    def task_sent(self, event):
        pass

    def task_received(self, event):
        pass

    def task_started(self, event):
        self._handle(tasks_api.TASK_STARTED, event, send_event=True)

    def task_succeeded(self, event):
        self._handle(tasks_api.TASK_SUCCEEDED, event, send_event=True)

    def task_failed(self, event):
        if event.get('exception', '').startswith(OperationRetry.__name__):
            state = tasks_api.TASK_RESCHEDULED
        else:
            state = tasks_api.TASK_FAILED
        self._handle(state, event, send_event=False)

    def task_revoked(self, event):
        pass

    def task_retried(self, event):
        pass

    def _handle(self, state, event, send_event):
        task_id = event['uuid']
        task = self.tasks_graph.get_task(task_id)
        if task is not None:
            if send_event:
                send_task_event(state, task, send_task_event_func_remote,
                                event)
            task.set_state(state)

    def capture(self):
        # Only called when running within an agent, so import here
        from cloudify_agent.app import app
        with app.connection() as connection:
            self._receiver = app.events.Receiver(connection, handlers={
                'task-sent': self.task_sent,
                'task-received': self.task_received,
                'task-started': self.task_started,
                'task-succeeded': self.task_succeeded,
                'task-failed': self.task_failed,
                'task-revoked': self.task_revoked,
                'task-retried': self.task_retried
            })
            for _ in self._receiver.itercapture(limit=None,
                                                timeout=None,
                                                wakeup=True):
                if self._should_stop:
                    return

    def stop(self):
        self._should_stop = True
        self._receiver.should_stop = True


def send_task_event_func_remote(task, event_type, message,
                                additional_context=None):
    _send_task_event_func(task, event_type, message,
                          out_func=logs.amqp_event_out,
                          additional_context=additional_context)


def send_task_event_func_local(task, event_type, message,
                               additional_context=None):
    _send_task_event_func(task, event_type, message,
                          out_func=logs.stdout_event_out,
                          additional_context=additional_context)


def _send_task_event_func(task, event_type, message, out_func,
                          additional_context):
    if task.cloudify_context is None:
        logs.send_workflow_event(ctx=task.workflow_context,
                                 event_type=event_type,
                                 message=message,
                                 out_func=out_func,
                                 additional_context=additional_context)
    else:
        logs.send_task_event(cloudify_context=task.cloudify_context,
                             event_type=event_type,
                             message=message,
                             out_func=out_func,
                             additional_context=additional_context)


def _filter_task(task, state):
    return state != tasks_api.TASK_FAILED and not task.send_task_events


def send_task_event(state, task, send_event_func, event):
    """
    Send a task event delegating to 'send_event_func'
    which will send events to RabbitMQ or use the workflow context logger
    in local context

    :param state: the task state (valid: ['sending', 'started', 'rescheduled',
                  'succeeded', 'failed'])
    :param task: a WorkflowTask instance to send the event for
    :param send_event_func: function for actually sending the event somewhere
    :param event: a dict with either a result field or an exception fields
                  follows celery event structure but used by local tasks as
                  well
    """
    if _filter_task(task, state):
        return

    if state in (tasks_api.TASK_FAILED, tasks_api.TASK_RESCHEDULED,
                 tasks_api.TASK_SUCCEEDED) and event is None:
        raise RuntimeError('Event for task {0} is None'.format(task.name))

    if event and event.get('exception'):
        exception_str = str(event.get('exception'))
    else:
        exception_str = None

    if state == tasks_api.TASK_SENDING:
        message = "Sending task '{0}'".format(task.name)
        event_type = 'sending_task'
    elif state == tasks_api.TASK_STARTED:
        message = "Task started '{0}'".format(task.name)
        event_type = 'task_started'
    elif state == tasks_api.TASK_SUCCEEDED:
        result = str(event.get('result'))
        suffix = ' ({0})'.format(result) if result not in ("'None'",
                                                           'None') else ''
        message = "Task succeeded '{0}{1}'".format(task.name, suffix)
        event_type = 'task_succeeded'
    elif state == tasks_api.TASK_RESCHEDULED:
        message = "Task rescheduled '{0}'".format(task.name)
        if exception_str:
            message = '{0} -> {1}'.format(message, exception_str)
        event_type = 'task_rescheduled'
        task.error = exception_str
    elif state == tasks_api.TASK_FAILED:
        message = "Task failed '{0}'".format(task.name)
        if exception_str:
            message = "{0} -> {1}".format(message, exception_str)
        event_type = 'task_failed'
        task.error = exception_str
    else:
        raise RuntimeError('unhandled event type: {0}'.format(state))

    if task.current_retries > 0:
        retry = ' [retry {0}{1}]'.format(
            task.current_retries,
            '/{0}'.format(task.total_retries)
            if task.total_retries >= 0 else '')
        message = '{0}{1}'.format(message, retry)

    additional_context = {
        'task_current_retries': task.current_retries,
        'task_total_retries': task.total_retries
    }

    if state in (tasks_api.TASK_FAILED, tasks_api.TASK_RESCHEDULED):
        additional_context['task_error_causes'] = event.get('causes')

    send_event_func(task=task,
                    event_type=event_type,
                    message=message,
                    additional_context=additional_context)
