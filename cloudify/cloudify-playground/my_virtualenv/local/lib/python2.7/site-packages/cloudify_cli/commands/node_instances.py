########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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
# * See the License for the specific language governing permissions and
#    * limitations under the License.

"""
Handles all commands that start with 'cfy node-instances'
"""

from cloudify_rest_client.exceptions import CloudifyClientError

from cloudify_cli import utils
from cloudify_cli.logger import get_logger
from cloudify_cli.exceptions import CloudifyCliError


def get(node_instance_id):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)

    logger.info('Retrieving node instance {0}'.format(node_instance_id))
    try:
        node_instance = client.node_instances.get(node_instance_id)
    except CloudifyClientError as e:
        if e.status_code != 404:
            raise
        raise CloudifyCliError('Node instance {0} not found')

    columns = ['id', 'deployment_id', 'host_id', 'node_id', 'state']
    pt = utils.table(columns, [node_instance])
    pt.max_width = 50
    utils.print_table('Instance:', pt)

    # print node instance runtime properties
    logger.info('Instance runtime properties:')
    for prop_name, prop_value in utils.decode_dict(
            node_instance.runtime_properties).iteritems():
        logger.info('\t{0}: {1}'.format(prop_name, prop_value))
    logger.info('')


def ls(deployment_id, node_name=None):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)
    try:
        if deployment_id:
            logger.info('Listing instances for deployment {0}...'.format(
                deployment_id))
        else:
            logger.info('Listing all instances...')
        instances = client.node_instances.list(deployment_id=deployment_id,
                                               node_name=node_name)
    except CloudifyClientError as e:
        if not e.status_code != 404:
            raise
        raise CloudifyCliError('Deployment {0} does not exist'.format(
            deployment_id))

    columns = ['id', 'deployment_id', 'host_id', 'node_id', 'state']
    pt = utils.table(columns, instances)
    utils.print_table('Instances:', pt)
