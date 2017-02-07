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
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

"""
Handles all commands that start with 'cfy plugins'
"""
import tarfile

from cloudify_cli import utils
from cloudify_cli.logger import get_logger
from cloudify_cli.utils import print_table
from cloudify_cli.exceptions import CloudifyCliError


def validate(plugin_path):
    logger = get_logger()

    logger.info('Validating plugin {0}...'.format(plugin_path.name))
    if not tarfile.is_tarfile(plugin_path.name):
        raise CloudifyCliError('Archive {0} is of an unsupported type. Only '
                               'tar.gz is allowed'.format(plugin_path.name))
    with tarfile.open(plugin_path.name, 'r') as tar:
        tar_members = tar.getmembers()
        package_json_path = "{0}/{1}".format(tar_members[0].name,
                                             'package.json')
        try:
            package_member = tar.getmember(package_json_path)
        except KeyError:
            raise CloudifyCliError(
                'Failed to validate plugin {0} '
                '(package.json was not found in archive)'.format(plugin_path))
        try:
            tar.extractfile(package_member).read()
        except:
            raise CloudifyCliError(
                'Failed to validate plugin {0} '
                '(unable to read package.json)'.format(plugin_path))

    logger.info('Plugin validated successfully')


def delete(plugin_id, force):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)

    logger.info('Deleting plugin {0}...'.format(plugin_id))
    client.plugins.delete(plugin_id=plugin_id, force=force)

    logger.info('Plugin deleted')


def upload(plugin_path):
    server_ip = utils.get_management_server_ip()
    utils.upload_plugin(plugin_path, server_ip,
                        utils.get_rest_client(server_ip), validate)


def download(plugin_id,
             output):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    logger.info('Downloading plugin {0}...'.format(plugin_id))
    client = utils.get_rest_client(management_ip)
    target_file = client.plugins.download(plugin_id, output)
    logger.info('Plugin downloaded as {0}'.format(target_file))


fields = ['id', 'package_name', 'package_version', 'supported_platform',
          'distribution', 'distribution_release', 'uploaded_at']


def get(plugin_id):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)

    logger.info('Retrieving plugin {0}...'.format(plugin_id))
    plugin = client.plugins.get(plugin_id, _include=fields)

    pt = utils.table(fields, data=[plugin])
    print_table('Plugin:', pt)


def ls():
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    client = utils.get_rest_client(management_ip)

    logger.info('Listing all plugins...')
    plugins = client.plugins.list(_include=fields)

    pt = utils.table(fields, data=plugins)
    print_table('Plugins:', pt)
