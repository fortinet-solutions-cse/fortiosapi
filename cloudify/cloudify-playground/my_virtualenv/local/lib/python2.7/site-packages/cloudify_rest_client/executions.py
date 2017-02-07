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


class Execution(dict):
    """Cloudify workflow execution."""
    TERMINATED = 'terminated'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    PENDING = 'pending'
    STARTED = 'started'
    CANCELLING = 'cancelling'
    FORCE_CANCELLING = 'force_cancelling'
    END_STATES = [TERMINATED, FAILED, CANCELLED]

    def __init__(self, execution):
        self.update(execution)

    @property
    def id(self):
        """
        :return: The execution's id.
        """
        return self.get('id')

    @property
    def deployment_id(self):
        """
        :return: The deployment's id this execution is related to.
        """
        return self.get('deployment_id')

    @property
    def status(self):
        """
        :return: The execution's status.
        """
        return self.get('status')

    @property
    def error(self):
        """
        :return: The execution error in a case of failure, otherwise None.
        """
        return self.get('error')

    @property
    def workflow_id(self):
        """
        :return: The id of the workflow this execution represents.
        """
        return self.get('workflow_id')

    @property
    def parameters(self):
        """
        :return: The execution's parameters
        """
        return self.get('parameters')

    @property
    def is_system_workflow(self):
        """
        :return: True if the workflow executed is a system workflow, otherwise
         False
        """
        return self.get('is_system_workflow', False)

    @property
    def created_at(self):
        """
        :return: The execution creation time.
        """
        return self.get('created_at')


class ExecutionsClient(object):

    def __init__(self, api):
        self.api = api

    def list(self, deployment_id=None, include_system_workflows=False,
             _include=None, **kwargs):
        """Returns a list of executions.

        :param deployment_id: Optional deployment id to get executions for.
        :param include_system_workflows: Include executions of system
               workflows
        :param _include: List of fields to include in response.
        :param kwargs: Optional filter fields. For a list of available fields
               see the REST service's models.Execution.fields
        :return: Executions list.
        """
        uri = '/executions'
        params = {'_include_system_workflows': include_system_workflows}
        if deployment_id:
            params['deployment_id'] = deployment_id
        params.update(kwargs)

        response = self.api.get(uri, params=params, _include=_include)
        return ListResponse([Execution(item) for item in response['items']],
                            response['metadata'])

    def get(self, execution_id, _include=None):
        """Get execution by its id.

        :param execution_id: Id of the execution to get.
        :param _include: List of fields to include in response.
        :return: Execution.
        """
        assert execution_id
        uri = '/executions/{0}'.format(execution_id)
        response = self.api.get(uri, _include=_include)
        return Execution(response)

    def update(self, execution_id, status, error=None):
        """Update execution with the provided status and optional error.

        :param execution_id: Id of the execution to update.
        :param status: Updated execution status.
        :param error: Updated execution error (optional).
        :return: Updated execution.
        """

        uri = '/executions/{0}'.format(execution_id)
        params = {'status': status}
        if error:
            params['error'] = error
        response = self.api.patch(uri, data=params)
        return Execution(response)

    def start(self, deployment_id, workflow_id, parameters=None,
              allow_custom_parameters=False, force=False):
        """Starts a deployment's workflow execution whose id is provided.

        :param deployment_id: The deployment's id to execute a workflow for.
        :param workflow_id: The workflow to be executed id.
        :param parameters: Parameters for the workflow execution.
        :param allow_custom_parameters: Determines whether to allow
         parameters which weren't defined in the workflow parameters schema
         in the blueprint.
        :param force: Determines whether to force the execution of the workflow
         in a case where there's an already running execution for this
         deployment.
        :raises: IllegalExecutionParametersError
        :return: The created execution.
        """
        assert deployment_id
        assert workflow_id
        data = {
            'deployment_id': deployment_id,
            'workflow_id': workflow_id,
            'parameters': parameters,
            'allow_custom_parameters': str(allow_custom_parameters).lower(),
            'force': str(force).lower()
        }
        uri = '/executions'
        response = self.api.post(uri,
                                 data=data,
                                 expected_status_code=201)
        return Execution(response)

    def cancel(self, execution_id, force=False):
        """Cancels the execution which matches the provided execution id.

        :param execution_id: Id of the execution to cancel.
        :param force: Boolean describing whether to send a 'cancel' or a 'force-cancel' action  # NOQA
        :return: Cancelled execution.
        """
        uri = '/executions/{0}'.format(execution_id)
        action = 'force-cancel' if force else 'cancel'
        response = self.api.post(uri,
                                 data={'action': action},
                                 expected_status_code=200)
        return Execution(response)
