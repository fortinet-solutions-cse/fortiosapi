#########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

import abc
import contextlib
import urllib2

import requests
from retrying import retry

from dsl_parser import exceptions

DEFAULT_RETRY_DELAY = 1
MAX_NUMBER_RETRIES = 5
DEFAULT_REQUEST_TIMEOUT = 10


class AbstractImportResolver(object):
    """
    This class is abstract and should be inherited by concrete
    implementations of import resolver.
    The only mandatory implementation is of resolve, which is expected
    to open the import url and return its data.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def resolve(self, import_url):
        raise NotImplementedError

    def fetch_import(self, import_url):
        url_parts = import_url.split(':')
        if url_parts[0] in ['http', 'https', 'ftp']:
            return self.resolve(import_url)
        return read_import(import_url)


def read_import(import_url):
    error_str = 'Import failed: Unable to open import url'
    if import_url.startswith('file:'):
        try:
            with contextlib.closing(urllib2.urlopen(import_url)) as f:
                return f.read()
        except Exception, ex:
            ex = exceptions.DSLParsingLogicException(
                13, '{0} {1}; {2}'.format(error_str, import_url, ex))
            raise ex
    else:
        number_of_attempts = MAX_NUMBER_RETRIES + 1

        # Defines on which errors we should retry the import.
        def _is_recoverable_error(e):
            return isinstance(e, (requests.ConnectionError, requests.Timeout))

        # Defines on which return values we should retry the import.
        def _is_internal_error(result):
            return hasattr(result, 'status_code') and result.status_code >= 500

        @retry(stop_max_attempt_number=number_of_attempts,
               wait_fixed=DEFAULT_RETRY_DELAY,
               retry_on_exception=_is_recoverable_error,
               retry_on_result=_is_internal_error)
        def get_import():
            response = requests.get(import_url,
                                    timeout=DEFAULT_REQUEST_TIMEOUT)
            # The response is a valid one, and the content should be returned
            if 200 <= response.status_code < 300:
                return response.text
            # If the response status code is above 500, an internal server
            # error has occurred. The return value would be caught by
            # _is_internal_error (as specified in the decorator), and retried.
            elif response.status_code >= 500:
                return response
            # Any other response should raise an exception.
            else:
                invalid_url_err = exceptions.DSLParsingLogicException(
                    13, '{0} {1}; status code: {2}'.format(
                        error_str, import_url, response.status_code))
                raise invalid_url_err

        try:
            import_result = get_import()
            # If the error is an internal error only. A custom exception should
            # be raised.
            if _is_internal_error(import_result):
                msg = 'Import failed {0} times, due to internal server error' \
                      '; {1}'.format(number_of_attempts, import_result.text)
                raise exceptions.DSLParsingLogicException(13, msg)
            return import_result
        # If any ConnectionError, Timeout or URLRequired should rise
        # after the retrying mechanism, a custom exception will be raised.
        except (requests.ConnectionError, requests.Timeout,
                requests.URLRequired) as err:

            raise exceptions.DSLParsingLogicException(
                13, '{0} {1}; {2}'.format(error_str, import_url, err))
