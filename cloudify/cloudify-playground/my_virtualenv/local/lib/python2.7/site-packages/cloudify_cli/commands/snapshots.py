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
Handles all commands that start with 'cfy snapshots'
"""

from cloudify_cli import utils
from cloudify_cli.logger import get_logger
from cloudify_cli.utils import print_table


def restore(snapshot_id, without_deployments_envs, force):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    logger.info('Restoring snapshot {0}...'.format(snapshot_id))
    client = utils.get_rest_client(management_ip)
    execution = client.snapshots.restore(
        snapshot_id, not without_deployments_envs, force)
    logger.info("Started workflow execution. The execution's id is {0}".format(
        execution.id))


def create(snapshot_id, include_metrics, exclude_credentials):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    logger.info('Creating snapshot {0}...'.format(snapshot_id))
    client = utils.get_rest_client(management_ip)
    execution = client.snapshots.create(snapshot_id,
                                        include_metrics,
                                        not exclude_credentials)
    logger.info("Started workflow execution. The execution's id is {0}".format(
        execution.id))


def delete(snapshot_id):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    logger.info('Deleting snapshot {0}...'.format(snapshot_id))
    client = utils.get_rest_client(management_ip)
    client.snapshots.delete(snapshot_id)
    logger.info('Snapshot deleted successfully')


def upload(snapshot_path, snapshot_id):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    logger.info('Uploading snapshot {0}...'.format(snapshot_path.name))
    client = utils.get_rest_client(management_ip)
    snapshot = client.snapshots.upload(snapshot_path.name, snapshot_id)
    logger.info("Snapshot uploaded. The snapshot's id is {0}".format(
        snapshot.id))


def download(snapshot_id, output):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    logger.info('Downloading snapshot {0}...'.format(snapshot_id))
    client = utils.get_rest_client(management_ip)
    target_file = client.snapshots.download(snapshot_id, output)
    logger.info('Snapshot downloaded as {0}'.format(target_file))


def ls():
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)
    logger.info('Listing snapshots...')
    pt = utils.table(['id', 'created_at', 'status', 'error'],
                     data=client.snapshots.list())
    print_table('Snapshots:', pt)
