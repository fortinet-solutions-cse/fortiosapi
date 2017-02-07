########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
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
import logging
import json
import datetime
from functools import wraps

from cloudify import amqp_client
from cloudify import amqp_client_utils
from cloudify import event as _event
from cloudify.exceptions import ClosedAMQPClientException

EVENT_CLASS = _event.Event
EVENT_VERBOSITY_LEVEL = _event.NO_VERBOSE


def message_context_from_cloudify_context(ctx):
    """Build a message context from a CloudifyContext instance"""
    from cloudify.context import NODE_INSTANCE, RELATIONSHIP_INSTANCE

    context = {
        'blueprint_id': ctx.blueprint.id,
        'deployment_id': ctx.deployment.id,
        'execution_id': ctx.execution_id,
        'workflow_id': ctx.workflow_id,
        'task_id': ctx.task_id,
        'task_name': ctx.task_name,
        'task_queue': ctx.task_queue,
        'task_target': ctx.task_target,
        'operation': ctx.operation.name,
        'plugin': ctx.plugin,
    }
    if ctx.type == NODE_INSTANCE:
        context['node_id'] = ctx.instance.id
        context['node_name'] = ctx.node.name
    elif ctx.type == RELATIONSHIP_INSTANCE:
        context['source_id'] = ctx.source.instance.id
        context['source_name'] = ctx.source.node.name
        context['target_id'] = ctx.target.instance.id
        context['target_name'] = ctx.target.node.name

    return context


def message_context_from_workflow_context(ctx):
    """Build a message context from a CloudifyWorkflowContext instance"""
    return {
        'blueprint_id': ctx.blueprint.id,
        'deployment_id': ctx.deployment.id,
        'execution_id': ctx.execution_id,
        'workflow_id': ctx.workflow_id,
    }


def message_context_from_sys_wide_wf_context(ctx):
    """Build a message context from a CloudifyWorkflowContext instance"""
    return {
        'blueprint_id': None,
        'deployment_id': None,
        'execution_id': ctx.execution_id,
        'workflow_id': ctx.workflow_id,
    }


def message_context_from_workflow_node_instance_context(ctx):
    """Build a message context from a CloudifyWorkflowNode instance"""
    message_context = message_context_from_workflow_context(ctx.ctx)
    message_context.update({
        'node_name': ctx.node_id,
        'node_id': ctx.id,
    })
    return message_context


class CloudifyBaseLoggingHandler(logging.Handler):
    """A base handler class for writing log messages to RabbitMQ"""

    def __init__(self, ctx, out_func, message_context_builder):
        logging.Handler.__init__(self)
        self.context = message_context_builder(ctx)
        self.out_func = out_func or amqp_log_out

    def flush(self):
        pass

    def emit(self, record):
        message = self.format(record)
        log = {
            'context': self.context,
            'logger': record.name,
            'level': record.levelname.lower(),
            'message': {
                'text': message
            }
        }
        self.out_func(log)


class CloudifyPluginLoggingHandler(CloudifyBaseLoggingHandler):
    """A handler class for writing plugin log messages to RabbitMQ"""
    def __init__(self, ctx, out_func=None):
        CloudifyBaseLoggingHandler.__init__(
            self, ctx, out_func, message_context_from_cloudify_context)


class CloudifyWorkflowLoggingHandler(CloudifyBaseLoggingHandler):
    """A Handler class for writing workflow log messages to RabbitMQ"""
    def __init__(self, ctx, out_func=None):
        CloudifyBaseLoggingHandler.__init__(
            self, ctx, out_func, message_context_from_workflow_context)


class SystemWideWorkflowLoggingHandler(CloudifyBaseLoggingHandler):
    """Class for writing system-wide workflow log messages to RabbitMQ"""
    def __init__(self, ctx, out_func=None):
        CloudifyBaseLoggingHandler.__init__(
            self, ctx, out_func, message_context_from_sys_wide_wf_context)


class CloudifyWorkflowNodeLoggingHandler(CloudifyBaseLoggingHandler):
    """A Handler class for writing workflow nodes log messages to RabbitMQ"""
    def __init__(self, ctx, out_func=None):
        CloudifyBaseLoggingHandler.__init__(
            self, ctx, out_func,
            message_context_from_workflow_node_instance_context)


def init_cloudify_logger(handler, logger_name,
                         logging_level=logging.DEBUG):
    """
    Instantiate an amqp backed logger based on the provided handler
    for sending log messages to RabbitMQ

    :param handler: A logger handler based on the context
    :param logger_name: The logger name
    :param logging_level: The logging level
    :return: An amqp backed logger
    """

    # TODO: somehow inject logging level (no one currently passes
    # logging_level)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging_level)
    for h in logger.handlers:
        logger.removeHandler(h)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(logging_level)
    logger.propagate = True
    logger.addHandler(handler)
    return logger


def send_workflow_event(ctx, event_type,
                        message=None,
                        args=None,
                        additional_context=None,
                        out_func=None):
    """Send a workflow event to RabbitMQ

    :param ctx: A CloudifyWorkflowContext instance
    :param event_type: The event type
    :param message: The message
    :param args: additional arguments that may be added to the message
    :param additional_context: additional context to be added to the context
    """
    _send_event(ctx, 'workflow', event_type, message, args,
                additional_context, out_func)


def send_sys_wide_wf_event(ctx, event_type, message=None, args=None,
                           additional_context=None, out_func=None):
    """Send a workflow event to RabbitMQ

    :param ctx: A CloudifySystemWideWorkflowContext instance
    :param event_type: The event type
    :param message: The message
    :param args: additional arguments that may be added to the message
    :param additional_context: additional context to be added to the context
    """
    _send_event(ctx, 'system_wide_workflow', event_type, message, args,
                additional_context, out_func)


def send_workflow_node_event(ctx, event_type,
                             message=None,
                             args=None,
                             additional_context=None,
                             out_func=None):
    """Send a workflow node event to RabbitMQ

    :param ctx: A CloudifyWorkflowNode instance
    :param event_type: The event type
    :param message: The message
    :param args: additional arguments that may be added to the message
    :param additional_context: additional context to be added to the context
    """
    _send_event(ctx, 'workflow_node', event_type, message, args,
                additional_context, out_func)


def send_plugin_event(ctx,
                      message=None,
                      args=None,
                      additional_context=None,
                      out_func=None):
    """Send a plugin event to RabbitMQ

    :param ctx: A CloudifyContext instance
    :param message: The message
    :param args: additional arguments that may be added to the message
    :param additional_context: additional context to be added to the context
    """
    _send_event(ctx, 'plugin', 'plugin_event', message, args,
                additional_context, out_func)


def send_task_event(cloudify_context,
                    event_type,
                    message=None,
                    args=None,
                    additional_context=None,
                    out_func=None):
    """Send a task event to RabbitMQ

    :param cloudify_context: a __cloudify_context struct as passed to
                             operations
    :param event_type: The event type
    :param message: The message
    :param args: additional arguments that may be added to the message
    :param additional_context: additional context to be added to the context
    """
    # import here to avoid cyclic dependencies
    from cloudify.context import CloudifyContext
    _send_event(CloudifyContext(cloudify_context),
                'task', event_type, message, args,
                additional_context,
                out_func)


def _send_event(ctx, context_type, event_type,
                message, args, additional_context,
                out_func):
    if context_type in ['plugin', 'task']:
        message_context = message_context_from_cloudify_context(
            ctx)
    elif context_type == 'workflow':
        message_context = message_context_from_workflow_context(ctx)
    elif context_type == 'workflow_node':
        message_context = message_context_from_workflow_node_instance_context(
            ctx)
    elif context_type == 'system_wide_workflow':
        message_context = message_context_from_sys_wide_wf_context(ctx)
    else:
        raise RuntimeError('Invalid context_type: {0}'.format(context_type))

    additional_context = additional_context or {}
    message_context.update(additional_context)

    event = {
        'event_type': event_type,
        'context': message_context,
        'message': {
            'text': message,
            'arguments': args
        }
    }
    out_func = out_func or amqp_event_out
    out_func(event)


def populate_base_item(item, message_type):
    timezone = time.strftime("%z", time.gmtime())
    timestamp = str(datetime.datetime.now())[0:-3] + timezone
    item['timestamp'] = timestamp
    item['message_code'] = None
    item['type'] = message_type


def amqp_event_out(event):
    populate_base_item(event, 'cloudify_event')
    _publish_message(event, 'event', logging.getLogger('cloudify_events'))


def amqp_log_out(log):
    populate_base_item(log, 'cloudify_log')
    _publish_message(log, 'log', logging.getLogger('cloudify_logs'))


def stdout_event_out(event):
    populate_base_item(event, 'cloudify_event')
    output = create_event_message_prefix(event)
    if output:
        sys.stdout.write('{0}\n'.format(output))
        sys.stdout.flush()


def stdout_log_out(log):
    populate_base_item(log, 'cloudify_log')
    output = create_event_message_prefix(log)
    if output:
        sys.stdout.write('{0}\n'.format(output))
        sys.stdout.flush()


def create_event_message_prefix(event):
    event_obj = EVENT_CLASS(event, verbosity_level=EVENT_VERBOSITY_LEVEL)
    if not event_obj.has_output:
        return None
    return str(event_obj)


def with_amqp_client(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        Calls the wrapped func with an AMQP client instance.
        Attempts to use a thread-local AMQP client, if exists; otherwise
        creates a new client and closes it after use.
        """
        # get an amqp client from the thread or create a new one
        fresh_client = False
        client = amqp_client_utils.get_amqp_client()
        if not client:
            client = amqp_client.create_client()
            fresh_client = True
        # call the wrapped func with the amqp client
        try:
            func(client, *args, **kwargs)
        except ClosedAMQPClientException:
            # the client has been closed, create a new one and call again
            client = amqp_client.create_client()
            fresh_client = True
            func(client, *args, **kwargs)
        finally:
            if fresh_client:
                client.close()

    return wrapper


@with_amqp_client
def _publish_message(client, message, message_type, logger):
    try:
        client.publish_message(message, message_type)
    except ClosedAMQPClientException:
        raise
    except BaseException as e:
        logger.warning(
            'Error publishing {0} to RabbitMQ ({1})[message={2}]'
            .format(message_type,
                    '{0}: {1}'.format(type(e).__name__, e),
                    json.dumps(message)))


class ZMQLoggingHandler(logging.Handler):

    def __init__(self, context, socket, fallback_logger):
        logging.Handler.__init__(self)
        self._context = context
        self._socket = socket
        self._fallback_logger = fallback_logger

    def emit(self, record):
        message = self.format(record)
        message = message.decode('utf-8', 'ignore').encode('utf-8')
        try:
            # Not using send_json to avoid possible deadlocks (see CFY-4866)
            self._socket.send(json.dumps({
                'context': self._context,
                'message': message
            }))
        except Exception as e:
            self._fallback_logger.warn(
                'Error sending message to logging server. ({0}: {1})'
                '[context={2}, message={3}]'
                .format(type(e).__name__, e, self._context, message))
