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

from cloudify_rest_client.responses import ListResponse


class Node(dict):
    """
    Cloudify node.
    """

    def __init__(self, node_instance):
        self.update(node_instance)

    @property
    def id(self):
        """
        :return: The identifier of the node.
        """
        return self.get('id')

    @property
    def deployment_id(self):
        """
        :return: The deployment id the node belongs to.
        """
        return self.get('deployment_id')

    @property
    def properties(self):
        """
        :return: The static properties of the node.
        """
        return self.get('properties')

    @property
    def operations(self):
        """
        :return: The node operations mapped to plugins.
        :rtype: dict
        """
        return self.get('operations')

    @property
    def relationships(self):
        """
        :return: The node relationships with other nodes.
        :rtype: list
        """
        return self.get('relationships')

    @property
    def blueprint_id(self):
        """
        :return: The id of the blueprint this node belongs to.
        :rtype: str
        """
        return self.get('blueprint_id')

    @property
    def plugins(self):
        """
        :return: The plugins this node has operations mapped to.
        :rtype: dict
        """
        return self.get('plugins')

    @property
    def number_of_instances(self):
        """
        :return: The number of instances this node has.
        :rtype: int
        """

        return int(self.get(
            'number_of_instances')) if 'number_of_instances' in self else None

    @property
    def planned_number_of_instances(self):
        """
        :return: The planned number of instances this node has.
        :rtype: int
        """

        return int(self.get(
            'planned_number_of_instances')) if 'planned_number_of_instances' \
                                               in self else None

    @property
    def deploy_number_of_instances(self):
        """
        :return: The number of instances this set for this node when the
                 deployment was created.
        :rtype: int
        """

        return int(self.get(
            'deploy_number_of_instances')) if 'deploy_number_of_instances' \
                                              in self else None

    @property
    def host_id(self):
        """
        :return: The id of the node instance which hosts this node.
        :rtype: str
        """
        return self.get('host_id')

    @property
    def type_hierarchy(self):
        """
        :return: The type hierarchy of this node.
        :rtype: list
        """
        return self['type_hierarchy']

    @property
    def type(self):
        """
        :return: The type of this node.
        :rtype: str
        """
        return self['type']


class NodesClient(object):

    def __init__(self, api):
        self.api = api

    def list(self, deployment_id=None, node_id=None, _include=None, **kwargs):
        """
        Returns a list of nodes which belong to the deployment identified
        by the provided deployment id.

        :param deployment_id: The deployment's id to list nodes for.
        :param node_id: If provided, returns only the requested node. This
                        parameter is deprecated, use 'id' instead.
        :param _include: List of fields to include in response.
        :param kwargs: Optional filter fields. for a list of available fields
               see the REST service's models.DeploymentNode.fields
        :return: Nodes.
        :rtype: list
        """
        params = {}
        if deployment_id:
            params['deployment_id'] = deployment_id
        if node_id:
            warnings.warn("'node_id' filtering capability is deprecated, use"
                          " 'id' instead", DeprecationWarning)
            params['id'] = node_id
        params.update(kwargs)
        if not params:
            params = None
        response = self.api.get('/nodes', params=params, _include=_include)
        return ListResponse([Node(item) for item in response['items']],
                            response['metadata'])

    def get(self, deployment_id, node_id, _include=None):
        """
        Returns the node which belongs to the deployment identified
        by the provided deployment id .

        :param deployment_id: The deployment's id of the node.
        :param node_id: The node id.
        :param _include: List of fields to include in response.
        :return: Nodes.
        :rtype: Node
        """
        assert deployment_id
        assert node_id
        result = self.list(deployment_id=deployment_id,
                           node_id=node_id,
                           _include=_include)
        if not result:
            return None
        else:
            return result[0]
