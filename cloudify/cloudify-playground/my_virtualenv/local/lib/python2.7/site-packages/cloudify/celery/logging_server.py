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

from __future__ import absolute_import

import functools
import json
import logging
import logging.handlers
import os
import random
import threading
import tempfile

import zmq
from celery import bootsteps
from celery.bin import Option
from celery.utils.log import get_logger

from cloudify.proxy import server
from cloudify.lru_cache import lru_cache

logger = get_logger(__name__)


LOGFILE_SIZE_BYTES = 5 * 1024 * 1024
LOGFILE_BACKUP_COUNT = 5


def configure_app(app):
    app.user_options['worker'].add(
        Option('--with-logging-server', action='store_true',
               default=False, help='Enable logging server'))
    app.user_options['worker'].add(
        Option('--logging-server-logdir', action='store',
               help='logdir location'))
    app.user_options['worker'].add(
        Option('--logging-server-handler-cache-size', action='store',
               type='int', default=100,
               help='Maximum number of file handlers that can be open at any '
                    'given time'))
    app.steps['worker'].add(ZMQLoggingServerBootstep)


class ZMQLoggingServerBootstep(bootsteps.StartStopStep):

    label = 'logging server'
    conditional = True

    def __init__(self, worker,
                 with_logging_server=False,
                 logging_server_logdir=None,
                 logging_server_handler_cache_size=100,
                 **kwargs):
        worker.logging_server = self
        self.enabled = with_logging_server
        self.logging_server = None
        self.logdir = logging_server_logdir
        self.cache_size = logging_server_handler_cache_size
        self.thread = None
        self.socket_url = None

    def info(self, worker):
        return {
            'logging_server': {
                'enabled': self.enabled,
                'logdir': self.logdir,
                'socket_url': self.socket_url,
                'cache_size': self.cache_size
            }
        }

    def start(self, worker):
        log_prefix = '| {0}: {1}'.format(type(worker).__name__, self.label)
        if not self.enabled:
            logger.debug('{0}: enabled={1}'.format(log_prefix, self.enabled))
            return
        if not self.logdir:
            raise ValueError('--logging-server-logdir must be supplied')
        if os.name == 'nt':
            self.socket_url = 'tcp://127.0.0.1:{0}'.format(
                server.get_unused_port())
        else:
            suffix = '%05x' % random.randrange(16 ** 5)
            self.socket_url = ('ipc://{0}/cloudify-logging-server-{1}.socket'
                               .format(tempfile.gettempdir(), suffix))
        if not os.path.exists(self.logdir):
            os.makedirs(self.logdir)
        self.logging_server = ZMQLoggingServer(socket_url=self.socket_url,
                                               logdir=self.logdir,
                                               cache_size=self.cache_size)
        self.thread = threading.Thread(target=self.logging_server.start)
        self.thread.start()
        logger.debug('{0}: enabled={1}, logdir={2}, socket_url={3}'
                     .format(log_prefix,
                             self.enabled,
                             self.logdir,
                             self.socket_url))

    def _stop_logging_server(self, worker):
        if not self.enabled:
            return
        self.logging_server.close()

    stop = _stop_logging_server
    close = _stop_logging_server
    shutdown = _stop_logging_server


class ZMQLoggingServer(object):

    def __init__(self, logdir, socket_url, cache_size):
        self.closed = False
        self.zmq_context = zmq.Context(io_threads=1)
        self.socket = self.zmq_context.socket(zmq.PULL)
        self.socket.bind(socket_url)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.logdir = logdir

        # on the management server, log files are handled by logrotate
        # with copytruncate so we use the simple FileHandler.
        # on agent hosts, we want to rotate the logs using python's
        # RotatingFileHandler.
        if os.environ.get('MGMTWORKER_HOME'):
            self.handler_func = logging.FileHandler
        else:
            self.handler_func = functools.partial(
                logging.handlers.RotatingFileHandler,
                maxBytes=LOGFILE_SIZE_BYTES,
                backupCount=LOGFILE_BACKUP_COUNT)

        # wrap the _get_handler method with an lru cache decorator
        # so we only keep the last 'cache_size' used handlers in in turn
        # have at most 'cache_size' file descriptors open
        cache_decorator = lru_cache(maxsize=cache_size,
                                    on_purge=lambda handler: handler.close())
        self._get_handler = cache_decorator(self._get_handler)

    def start(self):
        while not self.closed:
            try:
                if self.poller.poll(1000):
                    message = json.loads(self.socket.recv(), encoding='utf-8')
                    self._process(message)
            except Exception:
                if not self.closed:
                    logger.warning('Error raised during record processing',
                                   exc_info=True)

    def close(self):
        if not self.closed:
            self.closed = True
            self.socket.close()
            self.zmq_context.term()
            self._get_handler.clear()

    def _process(self, entry):
        handler = self._get_handler(entry['context'])
        handler.emit(Record(entry['message']))

    def _get_handler(self, handler_context):
        logfile = os.path.join(self.logdir, '{0}.log'.format(handler_context))
        handler = self.handler_func(logfile)
        handler.setFormatter(Formatter)
        return handler


class Record(object):
    def __init__(self, message):
        self.message = message
    filename = None
    lineno = None


class Formatter(object):
    @staticmethod
    def format(record):
        return record.message
