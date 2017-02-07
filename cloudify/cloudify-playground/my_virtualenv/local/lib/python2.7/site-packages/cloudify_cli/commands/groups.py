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
# * See the License for the specific language governing permissions and
#    * limitations under the License.

"""
Handles all commands that start with 'cfy groups'
"""

import json

from cloudify_cli import utils
from cloudify_cli.logger import get_logger
from cloudify_cli.exceptions import CloudifyCliError
from cloudify_rest_client.exceptions import CloudifyClientError


def ls(deployment_id):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)
    logger.info("Listing groups for deployment {0}...".format(
        deployment_id))
    try:
        deployment = client.deployments.get(deployment_id)
    except CloudifyClientError as e:
        if e.status_code != 404:
            raise
        raise CloudifyCliError('Deployment {0} not found'.format(
            deployment_id))

    groups = deployment.get('groups', {})
    scaling_groups = deployment.get('scaling_groups', {})

    if not groups:
        logger.info('No groups defined for deployment {0}'.format(
            deployment.id))
    else:
        logger.info("Groups: {0}".format(deployment.id))
        for group_name, group in groups.items():
            logger.info('  - Name: {0}'.format(group_name))
            logger.info('    Members: {0}'.format(
                json.dumps(group['members'])))
            group_policies = group.get('policies')
            scaling_group = scaling_groups.get(group_name)
            if group_policies or scaling_group:
                logger.info('    Policies:')
                if scaling_group:
                    logger.info('      - cloudify.policies.scaling')
                if group_policies:
                    for group_policy in group_policies.values():
                        logger.info('      - {0}'.format(group_policy['type']))
            logger.info('')
