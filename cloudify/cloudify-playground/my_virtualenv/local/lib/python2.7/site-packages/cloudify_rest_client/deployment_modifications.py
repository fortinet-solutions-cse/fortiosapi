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

from cloudify_rest_client.responses import ListResponse
from cloudify_rest_client.node_instances import NodeInstance


class DeploymentModificationNodeInstances(dict):

    def __init__(self, node_instances):
        self.update(node_instances)
        self['added_and_related'] = [NodeInstance(instance) for instance
                                     in self.get('added_and_related', [])]
        self['removed_and_related'] = [NodeInstance(instance) for instance
                                       in self.get('removed_and_related', [])]
        self['before_modification'] = [NodeInstance(instance) for instance
                                       in self.get('before_modification', [])]
        self['before_rollback'] = [NodeInstance(instance) for instance
                                   in self.get('before_rollback', [])]

    @property
    def added_and_related(self):
        """List of added nodes and nodes that are related to them"""
        return self['added_and_related']

    @property
    def removed_and_related(self):
        """List of removed nodes and nodes that are related to them"""
        return self['removed_and_related']

    @property
    def before_modification(self):
        """List of node instances with their state as it existed before the
        deployment modification started"""
        return self['before_modification']

    @property
    def before_rollback(self):
        """If deployment modification was rolledback, this will be a list of
        node instances with their state as it existed before the
        deployment modification was rolledback"""
        return self.get('before_rollback')


class DeploymentModification(dict):

    STARTED = 'started'
    FINISHED = 'finished'
    ROLLEDBACK = 'rolledback'

    def __init__(self, modification):
        self.update(modification)
        self['node_instances'] = DeploymentModificationNodeInstances(
            self.get('node_instances') or {})

    @property
    def id(self):
        """Deployment modification id"""
        return self['id']

    @property
    def status(self):
        """Deployment modification status"""
        return self['status']

    @property
    def deployment_id(self):
        """Deployment Id the outputs belong to."""
        return self['deployment_id']

    @property
    def node_instances(self):
        """Dict containing added_and_related and remove_and_related node
        instances list"""
        return self['node_instances']

    @property
    def modified_nodes(self):
        """Dict containing original modified nodes that started
        this modification"""
        return self['modified_nodes']

    @property
    def created_at(self):
        """Deployment modification creation date"""
        return self['created_at']

    @property
    def ended_at(self):
        """Deployment modification end date"""
        return self['ended_at']

    @property
    def context(self):
        """Dict containing context that has been attached to modification.

        This context has no predefined schema. Its structure can be whatever
        has been attached to the modification when it was started.
        """
        return self['context']


class DeploymentModificationsClient(object):

    def __init__(self, api):
        self.api = api

    def list(self, deployment_id=None, _include=None, **kwargs):
        """List deployment modifications

        :param deployment_id: The deployment id (optional)
        :param kwargs: Optional filter fields. for a list of available fields
               see the REST service's models.DeploymentModification.fields
        """

        params = {}
        if deployment_id:
            params['deployment_id'] = deployment_id
        params.update(kwargs)
        uri = '/deployment-modifications'

        response = self.api.get(uri, params=params, _include=_include)
        items = [DeploymentModification(item) for item in response['items']]
        return ListResponse(items, response['metadata'])

    def start(self, deployment_id, nodes, context=None):
        """Start deployment modification.

        :param deployment_id: The deployment id
        :param nodes: the nodes to modify
        :return: DeploymentModification dict
        :rtype: DeploymentModification
        """

        assert deployment_id
        data = {
            'deployment_id': deployment_id,
            'nodes': nodes
        }
        if context is not None:
            data['context'] = context

        uri = '/deployment-modifications'
        response = self.api.post(uri, data,
                                 expected_status_code=201)
        return DeploymentModification(response)

    def get(self, modification_id, _include=None):
        """Get  deployment modification

        :param modification_id: The modification id
        """
        uri = '/deployment-modifications/{0}'.format(modification_id)
        response = self.api.get(uri, _include=_include)
        return DeploymentModification(response)

    def finish(self, modification_id):
        """Finish deployment modification

        :param modification_id: The modification id
        """

        assert modification_id
        uri = '/deployment-modifications/{0}/finish'.format(modification_id)
        response = self.api.post(uri)
        return DeploymentModification(response)

    def rollback(self, modification_id):
        """Rollback deployment modification

        :param modification_id: The modification id
        """

        assert modification_id
        uri = '/deployment-modifications/{0}/rollback'.format(modification_id)
        response = self.api.post(uri)
        return DeploymentModification(response)
