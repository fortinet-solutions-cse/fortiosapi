########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

"""
Handles 'cfy uninstall'
"""

from cloudify_cli import utils
from cloudify_cli.commands import blueprints
from cloudify_cli.commands import executions
from cloudify_cli.commands import deployments
from cloudify_cli.constants import DEFAULT_UNINSTALL_WORKFLOW


def uninstall(deployment_id, workflow_id, parameters,
              allow_custom_parameters, timeout, include_logs, json):

    # Although the `uninstall` command does not use the `force` argument,
    # we are using the `executions start` handler as a part of it.
    # As a result, we need to provide it with a `force` argument, which is
    # defined below.
    force = False

    # if no workflow was supplied, execute the `uninstall` workflow
    if not workflow_id:
        workflow_id = DEFAULT_UNINSTALL_WORKFLOW

    executions.start(workflow_id=workflow_id,
                     deployment_id=deployment_id,
                     timeout=timeout,
                     force=force,
                     allow_custom_parameters=allow_custom_parameters,
                     include_logs=include_logs,
                     parameters=parameters,
                     json=json)

    # before deleting the deployment, save its blueprint_id, so we will be able
    # to delete the blueprint after deleting the deployment
    client = utils.get_rest_client()
    deployment = client.deployments.get(deployment_id,
                                        _include=['blueprint_id'])
    blueprint_id = deployment.blueprint_id

    deployments.delete(deployment_id, ignore_live_nodes=False)

    blueprints.delete(blueprint_id)
