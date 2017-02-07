#!/usr/bin/env python

import time
import json
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

RABBITMQ_SERVICE_NAME = 'rabbitmq'
ctx_properties = utils.ctx_factory.get(RABBITMQ_SERVICE_NAME)
rabbitmq_endpoint_ip = ctx_properties['rabbitmq_endpoint_ip']
PORT = 5671 if ctx_properties['rabbitmq_ssl_enabled'] else 5672


@utils.retry(ValueError)
def check_rabbit_running():
    """Use rabbitmqctl status to check if RabbitMQ is working.

    Sometimes rabbit takes a while to start, so this is retried several times.
    Note that this is currently impossible to do on a remote host, so
    this check only runs when rabbitmq is installed locally.
    """
    result = utils.sudo(['rabbitmqctl', 'status'], ignore_failures=True)
    if result.returncode != 0:
        raise ValueError('rabbitmqctl status: rabbitmq not running')


@utils.retry(ValueError)
def check_port_accessible(host, port):
    if not utils.is_port_open(port, host=host):
        raise ValueError('RabbitMQ is not listening at {0}:{1}'.format(
            host, port))


def set_rabbitmq_policy(name, expression, policy):
    policy = json.dumps(policy)
    ctx.logger.info('Setting policy {0} on queues {1} to {2}'.format(
        name, expression, policy))
    # shlex screws this up because we need to pass json and shlex
    # strips quotes so we explicitly pass it as a list.
    utils.sudo(['rabbitmqctl', 'set_policy', name,
               expression, policy, '--apply-to', 'queues'])


if not rabbitmq_endpoint_ip:
    ctx.logger.info("Starting RabbitMQ Service...")
    # rabbitmq restart exits with 143 status code that is valid in this case.
    utils.systemd.restart(RABBITMQ_SERVICE_NAME, ignore_failure=True)
    # This should be done in the create script.
    # For some reason, it fails. Need to check.

    events_queue_message_ttl = ctx_properties[
        'rabbitmq_events_queue_message_ttl']
    logs_queue_message_ttl = ctx_properties[
        'rabbitmq_logs_queue_message_ttl']
    metrics_queue_message_ttl = ctx_properties[
        'rabbitmq_metrics_queue_message_ttl']
    events_queue_length_limit = ctx_properties[
        'rabbitmq_events_queue_length_limit']
    logs_queue_length_limit = ctx_properties[
        'rabbitmq_logs_queue_length_limit']
    metrics_queue_length_limit = ctx_properties[
        'rabbitmq_metrics_queue_length_limit']

    utils.wait_for_port(5672)
    time.sleep(10)

    logs_queue_message_policy = {
        'message-ttl': logs_queue_message_ttl,
        'max-length': logs_queue_length_limit
    }
    events_queue_message_policy = {
        'message-ttl': events_queue_message_ttl,
        'max-length': events_queue_length_limit
    }
    metrics_queue_message_policy = {
        'message-ttl': metrics_queue_message_ttl,
        'max-length': metrics_queue_length_limit
    }
    riemann_deployment_queues_message_ttl = {
        'message-ttl': metrics_queue_message_ttl,
        'max-length': metrics_queue_length_limit
    }

    ctx.logger.info("Setting RabbitMQ Policies...")
    set_rabbitmq_policy(
        name='logs_queue_message_policy',
        expression='^cloudify-logs$',
        policy=logs_queue_message_policy
    )
    set_rabbitmq_policy(
        name='events_queue_message_policy',
        expression='^cloudify-events$',
        policy=events_queue_message_policy
    )
    set_rabbitmq_policy(
        name='metrics_queue_message_policy',
        expression='^amq\.gen.*$',
        policy=metrics_queue_message_policy
    )
    set_rabbitmq_policy(
        name='riemann_deployment_queues_message_ttl',
        expression='^.*-riemann$',
        policy=riemann_deployment_queues_message_ttl
    )

    # rabbitmq restart exits with 143 status code that is valid in this case.
    utils.start_service(RABBITMQ_SERVICE_NAME, ignore_restart_fail=True)
    rabbitmq_endpoint_ip = '127.0.0.1'

    utils.systemd.verify_alive(RABBITMQ_SERVICE_NAME)
    try:
        check_rabbit_running()
    except ValueError:
        ctx.abort_operation('Rabbitmq failed to start')

try:
    check_port_accessible(rabbitmq_endpoint_ip, PORT)
except ValueError:
    ctx.abort_operation('{0} error: port {1}:{2} was not open'.format(
        RABBITMQ_SERVICE_NAME, rabbitmq_endpoint_ip, PORT))
