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

import os

CONTENT_DISPOSITION_HEADER = 'content-disposition'
DEFAULT_BUFFER_SIZE = 8192


def request_data_file_stream_gen(file_path, buffer_size=DEFAULT_BUFFER_SIZE):
    with open(file_path, 'rb') as f:
        while True:
            read_bytes = f.read(buffer_size)
            yield read_bytes
            if len(read_bytes) < buffer_size:
                return


def write_response_stream_to_file(streamed_response, output_file=None,
                                  buffer_size=DEFAULT_BUFFER_SIZE):
    if not output_file:
        if CONTENT_DISPOSITION_HEADER not in streamed_response.headers:
            raise RuntimeError(
                'Cannot determine attachment filename: {0} header not'
                ' found in response headers'.format(
                    CONTENT_DISPOSITION_HEADER))
        output_file = streamed_response.headers[
            CONTENT_DISPOSITION_HEADER].split('filename=')[1]

    if os.path.exists(output_file):
        raise OSError("Output file '{0}' already exists".format(output_file))

    with open(output_file, 'wb') as f:
        for chunk in streamed_response.bytes_stream(buffer_size):
            if chunk:
                f.write(chunk)
                f.flush()

    return output_file
