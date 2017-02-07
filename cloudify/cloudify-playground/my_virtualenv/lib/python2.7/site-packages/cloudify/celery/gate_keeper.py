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

import collections
import threading
import logging
import Queue

from kombu.utils.encoding import safe_repr
from celery import bootsteps
from celery.bin import Option
from celery.utils.log import get_logger
from celery.worker.job import Request
from celery.worker.state import task_reserved

logger = get_logger(__name__)


def configure_app(app):
    app.user_options['worker'].add(
        Option('--with-gate-keeper', action='store_true',
               default=False, help='Enable gate keeper'))
    app.user_options['worker'].add(
        Option('--gate-keeper-bucket-size', action='store',
               type='int', default=5,
               help='The gate keeper bucket size'))
    app.steps['worker'].add(GateKeeper)


class GateKeeperStrategy(object):

    def _handle(self, request, callbacks):
        handle = self.handle
        gate_keeper = self.gate_keeper
        socket_url = self.logging_server_socket_url

        def handler():
            for callback in callbacks:
                callback()
            handle(request)
        if gate_keeper:
            gate_keeper.task_received(request, handler, socket_url)
        else:
            handler()

    def __init__(self, task, app, consumer,
                 info=logger.info,
                 task_reserved=task_reserved,
                 **kwargs):
        self.does_info = logger.isEnabledFor(logging.INFO)
        self.Request = Request
        self.app = app
        self.info = info
        self.task = task
        self.task_reserved = task_reserved
        self.hostname = consumer.hostname
        self.eventer = consumer.event_dispatcher
        self.events = self.eventer and self.eventer.enabled
        self.send_event = self.eventer.send
        self.connection_errors = consumer.connection_errors
        self.rate_limits_enabled = not consumer.disable_rate_limits
        self.get_bucket = consumer.task_buckets.__getitem__
        self.handle = consumer.on_task_request
        self.gate_keeper = getattr(consumer.controller, 'gate_keeper', None)
        logging_server = getattr(consumer.controller, 'logging_server', None)
        if logging_server:
            self.logging_server_socket_url = logging_server.socket_url
        else:
            self.logging_server_socket_url = None

    def __call__(self, message, body, ack, reject, callbacks, **kwargs):
        request = self._build_request(message, body, ack, reject)
        if request.revoked():
            return
        if request.eta:
            raise NotImplementedError('no eta support')
        if self.rate_limits_enabled and self.get_bucket(self.task.name):
            raise NotImplementedError('no rates limit support')
        if self.does_info:
            self.info('Received task: {0}'.format(request))
        if self.events:
            self._send_event(request)
        self.task_reserved(request)
        self._handle(request, callbacks or [])

    def _build_request(self, message, body, ack, reject):
        return self.Request(body, on_ack=ack, on_reject=reject,
                            app=self.app, hostname=self.hostname,
                            eventer=self.eventer, task=self.task,
                            connection_errors=self.connection_errors,
                            message=message)

    def _send_event(self, request):
        self.send_event(
            'task-received',
            uuid=request.id, name=request.name,
            args=safe_repr(request.args), kwargs=safe_repr(request.kwargs),
            retries=request.request_dict.get('retries', 0),
            eta=request.eta and request.eta.isoformat(),
            expires=request.expires and request.expires.isoformat())


class GateKeeper(bootsteps.StartStopStep):

    label = 'gate keeper'
    conditional = True

    def __init__(self, worker,
                 with_gate_keeper=False,
                 gate_keeper_bucket_size=5, **kwargs):
        worker.gate_keeper = self
        self.enabled = with_gate_keeper
        self.bucket_size = gate_keeper_bucket_size
        self._current = collections.defaultdict(
            lambda: Queue.Queue(self.bucket_size))
        self._on_hold = collections.defaultdict(Queue.Queue)
        self._lock = threading.Lock()

    def _noop(self, worker):
        pass

    stop = _noop
    close = _noop
    shutdown = _noop

    def info(self, worker):
        return {
            'gate_keeper': {
                'enabled': self.enabled,
                'bucket_size': self.bucket_size
            }
        }

    def start(self, worker):
        logger.debug('| {0}: {1}: enabled={2}, bucket_size={3}'
                     .format(type(worker).__name__,
                             self.label,
                             self.enabled,
                             self.bucket_size))

    def task_received(self, request, handler, socket_url=None):
        if not self.enabled:
            handler()
            return
        bucket_key = self._extract_bucket_key_and_augment_request(request,
                                                                  socket_url)
        if bucket_key:
            self._patch_request(bucket_key, request)
            self._lock.acquire()
            try:
                self._add_task(bucket_key)
            except Queue.Full:
                self._hold_task(bucket_key, handler)
                return
            finally:
                self._lock.release()
            # don't hold lock when calling handler, only getting here
            # if _add_task succeeded
            handler()
        else:
            handler()

    def task_ended(self, bucket_key):
        self._lock.acquire()
        try:
            self._clear_first_current_task(bucket_key)
            handler = self._try_get_on_hold_task(bucket_key)
            self._add_task(bucket_key)
        except Queue.Empty:
            return
        finally:
            self._lock.release()
        # don't hold lock when calling handler, only getting here
        # if on_hold queue was not empty
        handler()

    def _clear_first_current_task(self, bucket_key):
        self._current[bucket_key].get_nowait()

    def _try_get_on_hold_task(self, bucket_key):
        return self._on_hold[bucket_key].get_nowait()

    def _hold_task(self, bucket_key, handler):
        self._on_hold[bucket_key].put(handler)

    def _add_task(self, bucket_key):
        self._current[bucket_key].put_nowait(1)

    def _patch_request(self, bucket_key, request):
        # Intentionally not patching on_failure. It gets called
        # by the unfortunately named on_success which itself
        # gets called on successful *processing*, which does not necessarily
        # mean that the task finished successfully.
        task_ended = self.task_ended
        req_on_success = request.on_success

        def on_success(*args, **kwargs):
            req_on_success(*args, **kwargs)
            task_ended(bucket_key)
        request.on_success = on_success

    @staticmethod
    def _extract_bucket_key_and_augment_request(request, socket_url):
        cloudify_context = request.kwargs['__cloudify_context']
        if socket_url:
            cloudify_context['socket_url'] = socket_url
        deployment_id = cloudify_context.get('deployment_id')
        if deployment_id:
            task_type = cloudify_context['type']
            suffix = '_workflows' if task_type == 'workflow' else ''
            return '{0}{1}'.format(deployment_id, suffix)
        else:
            return None
