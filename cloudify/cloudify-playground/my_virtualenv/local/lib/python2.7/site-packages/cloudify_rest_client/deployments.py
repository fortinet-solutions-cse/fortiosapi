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

from cloudify_rest_client.responses import ListResponse


class Deployment(dict):
    """
    Cloudify deployment.
    """

    def __init__(self, deployment):
        self.update(deployment)
        if 'workflows' in self and self['workflows']:
            # might be None, for example in response for delete deployment
            self['workflows'] = [Workflow(item) for item in self['workflows']]

    @property
    def id(self):
        """
        :return: The identifier of the deployment.
        """
        return self.get('id')

    @property
    def blueprint_id(self):
        """
        :return: The identifier of the blueprint this deployment belongs to.
        """
        return self.get('blueprint_id')

    @property
    def workflows(self):
        """
        :return: The workflows of this deployment.
        """
        return self.get('workflows')

    @property
    def inputs(self):
        """
        :return: The inputs provided on deployment creation.
        """
        return self.get('inputs')

    @property
    def outputs(self):
        """
        :return: The outputs definition of this deployment.
        """
        return self.get('outputs')

    @property
    def description(self):
        """
        :return: The description of this deployment.
        """
        return self.get('description')


class Workflow(dict):

    def __init__(self, workflow):
        self.update(workflow)

    @property
    def id(self):
        """
        :return: The workflow's id
        """
        return self['name']

    @property
    def name(self):
        """
        :return: The workflow's name
        """
        return self['name']

    @property
    def parameters(self):
        """
        :return: The workflow's parameters
        """
        return self['parameters']


class DeploymentOutputs(dict):

    def __init__(self, outputs):
        self.update(outputs)

    @property
    def deployment_id(self):
        """Deployment Id the outputs belong to."""
        return self['deployment_id']

    @property
    def outputs(self):
        """Deployment outputs as dict."""
        return self['outputs']


class DeploymentOutputsClient(object):

    def __init__(self, api):
        self.api = api

    def get(self, deployment_id):
        """Gets the outputs for the provided deployment's Id.

        :param deployment_id: Deployment Id to get outputs for.
        :return: Outputs as dict.
        """
        assert deployment_id
        uri = '/deployments/{0}/outputs'.format(deployment_id)
        response = self.api.get(uri)
        return DeploymentOutputs(response)


class DeploymentsClient(object):

    def __init__(self, api):
        self.api = api
        self.outputs = DeploymentOutputsClient(api)

    def list(self, _include=None, **kwargs):
        """
        Returns a list of all deployments.

        :param _include: List of fields to include in response.
        :param kwargs: Optional filter fields. for a list of available fields
               see the REST service's models.Deployment.fields
        :return: Deployments list.
        """
        response = self.api.get('/deployments',
                                _include=_include,
                                params=kwargs)

        return ListResponse([Deployment(item) for item in response['items']],
                            response['metadata'])

    def get(self, deployment_id, _include=None):
        """
        Returns a deployment by its id.

        :param deployment_id: Id of the deployment to get.
        :param _include: List of fields to include in response.
        :return: Deployment.
        """
        assert deployment_id
        uri = '/deployments/{0}'.format(deployment_id)
        response = self.api.get(uri, _include=_include)
        return Deployment(response)

    def create(self, blueprint_id, deployment_id, inputs=None):
        """
        Creates a new deployment for the provided blueprint id and
        deployment id.

        :param blueprint_id: Blueprint id to create a deployment of.
        :param deployment_id: Deployment id of the new created deployment.
        :param inputs: Inputs dict for the deployment.
        :return: The created deployment.
        """
        assert blueprint_id
        assert deployment_id
        data = {
            'blueprint_id': blueprint_id
        }
        if inputs:
            data['inputs'] = inputs
        uri = '/deployments/{0}'.format(deployment_id)
        response = self.api.put(uri, data, expected_status_code=201)
        return Deployment(response)

    def delete(self, deployment_id, ignore_live_nodes=False):
        """
        Deletes the deployment whose id matches the provided deployment id.
        By default, deployment with live nodes deletion is not allowed and
        this behavior can be changed using the ignore_live_nodes argument.

        :param deployment_id: The deployment's to be deleted id.
        :param ignore_live_nodes: Determines whether to ignore live nodes.
        :return: The deleted deployment.
        """
        assert deployment_id
        params = {'ignore_live_nodes': 'true'} if ignore_live_nodes else None
        response = self.api.delete('/deployments/{0}'.format(deployment_id),
                                   params=params)
        return Deployment(response)
