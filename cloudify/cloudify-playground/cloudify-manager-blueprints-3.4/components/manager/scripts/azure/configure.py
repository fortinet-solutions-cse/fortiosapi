# #######
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
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
'''
    scripts.azure.configure
    ~~~~~~~~~~~~~~~~~~~~~~~
    Cloudify Manager configure script that creates a provider
    context configuration file for user deployments to use
'''

# Built-in Imports
import tempfile
from ConfigParser import ConfigParser
import os
# Third Party Imports
import fabric.api


def configure_manager(manager_config_path,
                      manager_config):
    '''Sets config defaults and creates the config file'''
    _, temp_config = tempfile.mkstemp()
    config = ConfigParser()

    config.add_section('Credentials')
    config.set('Credentials', 'subscription_id',
               manager_config['subscription_id'])
    config.set('Credentials', 'tenant_id',
               manager_config['tenant_id'])
    config.set('Credentials', 'client_id',
               manager_config['client_id'])
    config.set('Credentials', 'client_secret',
               manager_config['client_secret'])

    config.add_section('Azure')
    config.set('Azure', 'location',
               manager_config['location'])

    with open(temp_config, 'w') as temp_config_file:
        config.write(temp_config_file)

    fabric.api.sudo('mkdir -p {0}'.
                    format(os.path.dirname(manager_config_path)))
    fabric.api.put(temp_config,
                   manager_config_path,
                   use_sudo=True)
