#!/usr/bin/env python
#########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

import os
import urllib2
import json
import argparse
import sys


# Environment variable for the socket url
# (used by clients to locate the socket [http, zmq(unix, tcp)])
CTX_SOCKET_URL = 'CTX_SOCKET_URL'


class ScriptException(Exception):
    def __init__(self, message=None, retry=False):
        super(Exception, self).__init__(message)
        self.retry = retry


class RequestError(RuntimeError):

    def __init__(self, ex_message, ex_type, ex_traceback):
        super(RequestError, self).__init__(
            self,
            '{0}: {1}'.format(ex_type, ex_message))
        self.ex_type = ex_type
        self.ex_message = ex_message
        self.ex_traceback = ex_traceback


def zmq_client_req(socket_url, request, timeout):
    import zmq
    context = zmq.Context()
    sock = context.socket(zmq.REQ)
    try:
        sock.connect(socket_url)
        sock.send_json(request)
        if sock.poll(1000 * timeout):
            return sock.recv_json()
        else:
            raise RuntimeError('Timed out while waiting for response')
    finally:
        sock.close()
        context.term()


def http_client_req(socket_url, request, timeout):
    response = urllib2.urlopen(socket_url,
                               data=json.dumps(request),
                               timeout=timeout)
    if response.code != 200:
        raise RuntimeError('Request failed: {0}'.format(response))
    return json.loads(response.read())


def client_req(socket_url, args, timeout=5):
    request = {
        'args': args
    }

    schema, _ = socket_url.split('://')
    if schema in ['ipc', 'tcp']:
        request_method = zmq_client_req
    elif schema in ['http']:
        request_method = http_client_req
    else:
        raise RuntimeError('Unsupported protocol: {0}'.format(schema))

    response = request_method(socket_url, request, timeout)
    payload = response['payload']
    response_type = response.get('type')
    if response_type == 'error':
        ex_type = payload['type']
        ex_message = payload['message']
        ex_traceback = payload['traceback']
        raise RequestError(ex_message,
                           ex_type,
                           ex_traceback)
    elif response_type == 'stop_operation':
        raise SystemExit(payload['message'])
    else:
        return payload


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--timeout', type=int, default=30)
    parser.add_argument('--socket-url', default=os.environ.get(CTX_SOCKET_URL))
    parser.add_argument('--json-arg-prefix', default='@')
    parser.add_argument('-j', '--json-output', action='store_true')
    parser.add_argument('args', nargs='*')
    args = parser.parse_args(args)
    if not args.socket_url:
        raise RuntimeError('Missing CTX_SOCKET_URL environment variable'
                           ' or socket_url command line argument')
    return args


def process_args(json_prefix, args):
    processed_args = []
    for arg in args:
        if arg.startswith(json_prefix):
            arg = json.loads(arg[1:])
        processed_args.append(arg)
    return processed_args


def main(args=None):
    args = parse_args(args)
    response = client_req(args.socket_url,
                          process_args(args.json_arg_prefix,
                                       args.args),
                          args.timeout)
    if args.json_output:
        response = json.dumps(response)
    else:
        if not response:
            response = ''
        response = str(response)
    sys.stdout.write(response)


if __name__ == '__main__':
    main()
