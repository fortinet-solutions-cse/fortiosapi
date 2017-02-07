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

import warnings
from datetime import datetime

from cloudify_rest_client.responses import ListResponse


class EventsClient(object):

    def __init__(self, api):
        self.api = api

    def get(self,
            execution_id,
            from_event=0,
            batch_size=100,
            include_logs=False):
        """
        Returns event for the provided execution id.

        :param execution_id: Id of execution to get events for.
        :param from_event: Index of first event to retrieve on pagination.
        :param batch_size: Maximum number of events to retrieve per call.
        :param include_logs: Whether to also get logs.
        :return: Events list and total number of currently available
         events (tuple).
        """
        warnings.warn('method is deprecated, use "{0}" method instead'
                      .format(self.list.__name__),
                      DeprecationWarning)

        response = self.list(execution_id=execution_id,
                             include_logs=include_logs,
                             _offset=from_event,
                             _size=batch_size,
                             _sort='@timestamp')
        events = response.items
        total_events = response.metadata.pagination.total
        return events, total_events

    def list(self, include_logs=False, message=None,
             from_datetime=None, to_datetime=None,
             _include=None, **kwargs):
        """List events

        :param include_logs: Whether to also get logs.
        :param message: an expression used for wildcard search events
                        by their message text
        :param from_datetime: search for events later or equal to datetime
        :param to_datetime: search for events earlier or equal to datetime
        :param _include: return only an exclusive list of fields
        :return: dict with 'metadata' and 'items' fields
        """

        uri = '/events'
        params = kwargs
        if message:
            params['message.text'] = str(message)

        params['type'] = ['cloudify_event']
        if include_logs:
            params['type'].append('cloudify_log')

        timestamp_range = dict()

        if from_datetime:
            # if a datetime instance, convert to iso format
            timestamp_range['from'] = \
                from_datetime.isoformat() if isinstance(
                    from_datetime, datetime) else from_datetime

        if to_datetime:
            timestamp_range['to'] = \
                to_datetime.isoformat() if isinstance(
                    to_datetime, datetime) else to_datetime

        if timestamp_range:
            params['_range'] = params.get('_range', [])
            params['_range'].append('@timestamp,{0},{1}'
                                    .format(timestamp_range.get('from', ''),
                                            timestamp_range.get('to', '')))

        response = self.api.get(uri,
                                _include=_include,
                                params=params)
        return ListResponse(response['items'], response['metadata'])
