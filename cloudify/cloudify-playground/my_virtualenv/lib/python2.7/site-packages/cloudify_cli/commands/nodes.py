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
Handles all commands that start with 'cfy nodes'
"""
from cloudify_rest_client.exceptions import CloudifyClientError

from cloudify_cli import utils
from cloudify_cli.logger import get_logger
from cloudify_cli.exceptions import CloudifyCliError


def get(deployment_id, node_id):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)

    logger.info('Retrieving node {0} for deployment {1}'.format(
        node_id, deployment_id))
    try:
        node = client.nodes.get(deployment_id, node_id)
    except CloudifyClientError as e:
        if e.status_code != 404:
            raise
        raise CloudifyCliError('Node {0} was not found'.format(node_id))

    logger.debug('Getting node instances for node with ID \'{0}\''
                 .format(node_id))
    try:
        instances = client.node_instances.list(deployment_id, node_id)
    except CloudifyClientError as e:
        if e.status_code != 404:
            raise

    # print node parameters
    columns = ['id', 'deployment_id', 'blueprint_id', 'host_id', 'type',
               'number_of_instances', 'planned_number_of_instances']
    pt = utils.table(columns, [node])
    pt.max_width = 50
    utils.print_table('Node:', pt)

    # print node properties
    logger.info('Node properties:')
    for property_name, property_value in utils.decode_dict(
            node.properties).iteritems():
        logger.info('\t{0}: {1}'.format(property_name, property_value))
    logger.info('')

    # print node instances IDs
    logger.info('Node instance IDs:')
    if instances:
        for instance in instances:
            logger.info('\t{0}'.format(instance['id']))
    else:
        logger.info('\tNo node instances')


def ls(deployment_id):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)
    try:
        if deployment_id:
            logger.info('Listing nodes for deployment {0}...'.format(
                deployment_id))
        else:
            logger.info('Listing all nodes...')
        nodes = client.nodes.list(deployment_id=deployment_id)
    except CloudifyClientError as e:
        if not e.status_code != 404:
            raise
        raise CloudifyCliError('Deployment {0} does not exist'.format(
            deployment_id))

    columns = ['id', 'deployment_id', 'blueprint_id', 'host_id', 'type',
               'number_of_instances', 'planned_number_of_instances']
    pt = utils.table(columns, nodes)
    utils.print_table('Nodes:', pt)
