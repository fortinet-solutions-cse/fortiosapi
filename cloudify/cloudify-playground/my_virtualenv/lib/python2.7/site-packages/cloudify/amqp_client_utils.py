########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
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

from threading import Thread, local as thread_local
from Queue import Queue

from cloudify import amqp_client


thread_storage = thread_local()


class AMQPWrappedThread(Thread):
    """
    creates an amqp client before calling the target method.
    This thread is always set as a daemon.
    """

    def __init__(self, target, *args, **kwargs):

        def wrapped_target(*inner_args, **inner_kwargs):
            client = amqp_client.create_client()
            self.started_amqp_client.put_nowait(True)
            thread_storage.amqp_client = client
            try:
                self.target_method(*inner_args, **inner_kwargs)
            finally:
                client.close()

        self.target_method = target
        super(AMQPWrappedThread, self).__init__(target=wrapped_target, *args,
                                                **kwargs)
        self.started_amqp_client = Queue(1)
        self.daemon = True


def init_amqp_client():
    thread_storage.amqp_client = amqp_client.create_client()


def get_amqp_client():
    return getattr(thread_storage, 'amqp_client', None)


def close_amqp_client():
    client = get_amqp_client()
    if client:
        client.close()
