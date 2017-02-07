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


import json
import logging
import threading

import pika
import pika.exceptions

from cloudify import broker_config
from cloudify import exceptions
from cloudify import utils

logger = logging.getLogger(__name__)


class AMQPClient(object):

    EVENTS_QUEUE_NAME = 'cloudify-events'
    LOGS_QUEUE_NAME = 'cloudify-logs'
    channel_settings = {
        'auto_delete': True,
        'durable': True,
        'exclusive': False
    }

    def __init__(self,
                 amqp_user='guest',
                 amqp_pass='guest',
                 amqp_host=None,
                 ssl_enabled=False,
                 ssl_cert_path=''):
        self.connection = None
        self.channel = None
        self._is_closed = False
        if amqp_host is None:
            amqp_host = utils.get_manager_ip()
        credentials = pika.credentials.PlainCredentials(
            username=amqp_user,
            password=amqp_pass)
        amqp_port, ssl_options = utils.internal.get_broker_ssl_and_port(
            ssl_enabled=ssl_enabled,
            cert_path=ssl_cert_path)
        self._connection_parameters = pika.ConnectionParameters(
                host=amqp_host,
                port=amqp_port,
                credentials=credentials,
                ssl=ssl_enabled,
                ssl_options=ssl_options)
        self._connect()

    def _connect(self):
        self.connection = pika.BlockingConnection(self._connection_parameters)
        self.channel = self.connection.channel()
        self.channel.confirm_delivery()
        for queue in [self.EVENTS_QUEUE_NAME, self.LOGS_QUEUE_NAME]:
            self.channel.queue_declare(queue=queue, **self.channel_settings)

    def publish_message(self, message, message_type):
        if self._is_closed:
            raise exceptions.ClosedAMQPClientException(
                'Publish failed, AMQP client already closed')
        if message_type == 'event':
            routing_key = self.EVENTS_QUEUE_NAME
        else:
            routing_key = self.LOGS_QUEUE_NAME
        exchange = ''
        body = json.dumps(message)
        try:
            self.channel.basic_publish(exchange=exchange,
                                       routing_key=routing_key,
                                       body=body)
        except pika.exceptions.ConnectionClosed as e:
            logger.warn(
                'Connection closed unexpectedly for thread {0}, '
                'reconnecting. ({1}: {2})'
                .format(threading.current_thread(), type(e).__name__, repr(e)))
            # obviously, there is no need to close the current
            # channel/connection.
            self._connect()
            self.channel.basic_publish(exchange=exchange,
                                       routing_key=routing_key,
                                       body=body)

    def close(self):
        if self._is_closed:
            return
        self._is_closed = True
        thread = threading.current_thread()
        if self.channel:
            logger.debug('Closing amqp channel of thread {0}'.format(thread))
            try:
                self.channel.close()
            except Exception as e:
                # channel might be already closed, log and continue
                logger.debug('Failed to close amqp channel of thread {0}, '
                             'reported error: {1}'.format(thread, repr(e)))

        if self.connection:
            logger.debug('Closing amqp connection of thread {0}'
                         .format(thread))
            try:
                self.connection.close()
            except Exception as e:
                # connection might be already closed, log and continue
                logger.debug('Failed to close amqp connection of thread {0}, '
                             'reported error: {1}'.format(thread, repr(e)))


def create_client(amqp_host=broker_config.broker_hostname,
                  amqp_user=broker_config.broker_username,
                  amqp_pass=broker_config.broker_password,
                  ssl_enabled=broker_config.broker_ssl_enabled,
                  ssl_cert_path=broker_config.broker_cert_path):
    thread = threading.current_thread()
    try:
        logger.debug(
            'Creating a new AMQP client for thread {0} '
            '[hostname={1}, username={2}, ssl_enabled={3}, cert_path={4}]'
            .format(thread, amqp_host, amqp_user, ssl_enabled, ssl_cert_path))
        client = AMQPClient(amqp_host=amqp_host,
                            amqp_user=amqp_user,
                            amqp_pass=amqp_pass,
                            ssl_enabled=ssl_enabled,
                            ssl_cert_path=ssl_cert_path)
        logger.debug('AMQP client created for thread {0}'.format(thread))
    except Exception as e:
        logger.warning(
            'Failed to create AMQP client for thread: {0} ({1}: {2})'
            .format(thread, type(e).__name__, e))
        raise
    return client
