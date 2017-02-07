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

from cloudify_rest_client.exceptions import NotModifiedError


class Maintenance(dict):

    def __init__(self, maintenance_state):
        self.update(maintenance_state)

    @property
    def status(self):
        """
        :return: maintenance mode's status (activated, activating, deactivated)
        """
        return self.get('status')

    @property
    def activated_at(self):
        """
        :return: time of activating maintenance
                 mode (time of entering 'activate' mode).
        """
        return self.get('activated_at')

    @property
    def activation_requested_at(self):
        """
        :return: time of sending the request to start maintenance
                 mode (time of entering 'activating' mode).
        """
        return self.get('activation_requested_at')

    @property
    def remaining_executions(self):
        """
        :return: amount of running executions remaining before
                 maintenance mode is activated.
        """
        return self.get('remaining_executions', [])

    @property
    def requested_by(self):
        """
        :return: amount of running executions remaining before
                 maintenance mode is activated.
        """
        return self.get('requested_by')


class MaintenanceModeClient(object):

    def __init__(self, api):
        self.api = api

    def status(self):
        """

        :return: Maintenance mode state.
        """
        uri = '/maintenance'
        response = self.api.get(uri)
        return Maintenance(response)

    def activate(self):
        """
        Activates maintenance mode.

        :return: Maintenance mode state.
        """
        uri = '/maintenance/activate'
        try:
            response = self.api.post(uri)
        except NotModifiedError as e:
            e.message = 'Maintenance mode is already on.'
            raise
        return Maintenance(response)

    def deactivate(self):
        """
        Deactivates maintenance mode.

        :return: Maintenance mode state.
        """
        uri = '/maintenance/deactivate'
        try:
            response = self.api.post(uri)
        except NotModifiedError as e:
            e.message = 'Maintenance mode is already off.'
            raise
        return Maintenance(response)
