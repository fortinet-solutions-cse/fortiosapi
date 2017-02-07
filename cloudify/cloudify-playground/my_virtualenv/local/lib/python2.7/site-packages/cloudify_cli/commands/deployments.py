########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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
Handles all commands that start with 'cfy deployments'
"""

import os
from StringIO import StringIO

from cloudify_cli import utils
from cloudify_cli.logger import get_logger, get_events_logger
from cloudify_cli.exceptions import SuppressedCloudifyCliError
from cloudify_cli.execution_events_fetcher import wait_for_execution
from cloudify_rest_client.exceptions import UnknownDeploymentInputError
from cloudify_rest_client.exceptions import MissingRequiredDeploymentInputError


def _print_deployment_inputs(client, blueprint_id):
    logger = get_logger()
    blueprint = client.blueprints.get(blueprint_id)
    logger.info('Deployment inputs:')
    inputs_output = StringIO()
    for input_name, input_def in blueprint.plan['inputs'].iteritems():
        inputs_output.write('\t{0}:{1}'.format(input_name, os.linesep))
        for k, v in input_def.iteritems():
            inputs_output.write('\t\t{0}: {1}{2}'.format(k, v, os.linesep))
    inputs_output.write(os.linesep)
    logger.info(inputs_output.getvalue())


def ls(blueprint_id):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)
    if blueprint_id:
        logger.info('Listing deployments for blueprint {0}...'.format(
            blueprint_id))
    else:
        logger.info('Listing all deployments...')
    deployments = client.deployments.list()
    if blueprint_id:
        deployments = filter(lambda deployment:
                             deployment['blueprint_id'] == blueprint_id,
                             deployments)

    pt = utils.table(
        ['id',
         'blueprint_id',
         'created_at',
         'updated_at'],
        deployments)
    utils.print_table('Deployments:', pt)


def update(deployment_id,
           blueprint_path,
           inputs,
           blueprint_filename,
           archive_location,
           skip_install,
           skip_uninstall,
           workflow_id,
           force,
           include_logs,
           json):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)

    processed_inputs = utils.inputs_to_dict(inputs, 'inputs')

    blueprint_or_archive_path = blueprint_path.name \
        if blueprint_path else archive_location
    logger.info('Updating deployment {dep_id} using blueprint {path}'.format(
        dep_id=deployment_id, path=blueprint_or_archive_path))

    deployment_update = client.deployment_updates.update(
        deployment_id,
        blueprint_or_archive_path,
        application_file_name=blueprint_filename,
        inputs=processed_inputs,
        workflow_id=workflow_id,
        skip_install=skip_install,
        skip_uninstall=skip_uninstall,
        force=force)

    events_logger = get_events_logger(json)

    execution = wait_for_execution(
        client,
        client.executions.get(deployment_update.execution_id),
        events_handler=events_logger,
        include_logs=include_logs,
        timeout=None)  # don't timeout ever
    if execution.error:
        logger.info("Execution of workflow '{0}' for deployment "
                    "'{1}' failed. [error={2}]"
                    .format(execution.workflow_id,
                            execution.deployment_id,
                            execution.error))
        logger.info('Failed updating deployment {dep_id}. Deployment update '
                    'id: {depup_id}. Execution id: {exec_id}'
                    .format(depup_id=deployment_update.id,
                            dep_id=deployment_id,
                            exec_id=execution.id))
        raise SuppressedCloudifyCliError()
    else:
        logger.info("Finished executing workflow '{0}' on deployment "
                    "'{1}'".format(execution.workflow_id,
                                   execution.deployment_id))
        logger.info('Successfully updated deployment {dep_id}. '
                    'Deployment update id: {depup_id}. Execution id: {exec_id}'
                    .format(depup_id=deployment_update.id,
                            dep_id=deployment_id,
                            exec_id=execution.id))


def create(blueprint_id, deployment_id, inputs):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    inputs = utils.inputs_to_dict(inputs, 'inputs')

    logger.info('Creating new deployment from blueprint {0}...'.format(
        blueprint_id))
    client = utils.get_rest_client(management_ip)

    try:
        deployment = client.deployments.create(blueprint_id,
                                               deployment_id,
                                               inputs=inputs)
    except MissingRequiredDeploymentInputError as e:
        logger.info('Unable to create deployment. Not all '
                    'required inputs have been specified...')
        _print_deployment_inputs(client, blueprint_id)
        raise SuppressedCloudifyCliError(str(e))
    except UnknownDeploymentInputError as e:
        logger.info(
            'Unable to create deployment, an unknown input was specified...')
        _print_deployment_inputs(client, blueprint_id)
        raise SuppressedCloudifyCliError(str(e))

    logger.info("Deployment created. The deployment's id is {0}".format(
        deployment.id))


def delete(deployment_id, ignore_live_nodes):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    logger.info('Deleting deployment {0}...'.format(deployment_id))
    client = utils.get_rest_client(management_ip)
    client.deployments.delete(deployment_id, ignore_live_nodes)
    logger.info("Deployment deleted")


def outputs(deployment_id):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)

    logger.info('Retrieving outputs for deployment {0}...'.format(
        deployment_id))
    dep = client.deployments.get(deployment_id, _include=['outputs'])
    outputs_def = dep.outputs
    response = client.deployments.outputs.get(deployment_id)
    outputs_ = StringIO()
    for output_name, output in response.outputs.iteritems():
        outputs_.write(' - "{0}":{1}'.format(output_name, os.linesep))
        description = outputs_def[output_name].get('description', '')
        outputs_.write('     Description: {0}{1}'.format(description,
                                                         os.linesep))
        outputs_.write('     Value: {0}{1}'.format(output, os.linesep))
    logger.info(outputs_.getvalue())
