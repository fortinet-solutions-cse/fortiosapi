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

"""
Handles 'cfy use'
"""

from cloudify_rest_client.exceptions import (
    CloudifyClientError,
    UserUnauthorizedError
)

from cloudify_cli import utils
from cloudify_cli import constants
from cloudify_cli.logger import get_logger
from cloudify_cli.bootstrap import bootstrap as bs
from cloudify_cli.exceptions import CloudifyCliError


def use(management_ip, rest_port):
    logger = get_logger()
    # determine SSL mode by port
    if rest_port == constants.SECURED_REST_PORT:
        protocol = constants.SECURED_PROTOCOL
    else:
        protocol = constants.DEFAULT_PROTOCOL
    client = utils.get_rest_client(
        manager_ip=management_ip, rest_port=rest_port, protocol=protocol,
        skip_version_check=True)
    try:
        # first check this server is available.
        client.manager.get_status()
    except UserUnauthorizedError:
        msg = "Can't use manager {0}: User is unauthorized.".format(
            management_ip)
        raise CloudifyCliError(msg)
    except CloudifyClientError as e:
        msg = "Can't use manager {0}: {1}".format(management_ip, str(e))
        raise CloudifyCliError(msg)

    # check if cloudify was initialized.
    if not utils.is_initialized():
        utils.dump_cloudify_working_dir_settings()
        utils.dump_configuration_file()

    try:
        response = client.manager.get_context()
        provider_context = response['context']
    except CloudifyClientError:
        provider_context = None

    with utils.update_wd_settings() as wd_settings:
        wd_settings.set_management_server(management_ip)
        wd_settings.set_provider_context(provider_context)
        wd_settings.set_rest_port(rest_port)
        wd_settings.set_protocol(protocol)
        logger.info('Using manager {0} with port {1}'.format(
            management_ip, rest_port))

    # delete the previous manager deployment if exists.
    bs.delete_workdir()
