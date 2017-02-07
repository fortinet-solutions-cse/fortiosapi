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
Handles 'cfy init'
"""

import os
import shutil

from cloudify_cli import utils
from cloudify_cli import constants
from cloudify_cli import exceptions
from cloudify_cli.logger import get_logger
from cloudify_cli.logger import configure_loggers


def init(reset_config, skip_logging=False):
    if os.path.exists(os.path.join(
            utils.get_cwd(),
            constants.CLOUDIFY_WD_SETTINGS_DIRECTORY_NAME,
            constants.CLOUDIFY_WD_SETTINGS_FILE_NAME)):
        if not reset_config:
            error = exceptions.CloudifyCliError(
                'Current directory is already initialized')
            error.possible_solutions = [
                "Run 'cfy init -r' to force re-initialization "
                "(might overwrite existing "
                "configuration files if exist) "
            ]
            raise error
        else:
            shutil.rmtree(os.path.join(
                utils.get_cwd(),
                constants.CLOUDIFY_WD_SETTINGS_DIRECTORY_NAME))

    settings = utils.CloudifyWorkingDirectorySettings()
    utils.dump_cloudify_working_dir_settings(settings)
    utils.dump_configuration_file()
    configure_loggers()
    if not skip_logging:
        get_logger().info('Initialization completed successfully')
