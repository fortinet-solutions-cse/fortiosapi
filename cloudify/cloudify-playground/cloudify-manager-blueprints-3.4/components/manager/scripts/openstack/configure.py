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

import tempfile
import json
import os

import fabric.api

from cloudify import ctx
from openstack_plugin_common import (
    OPENSTACK_ID_PROPERTY,
    OPENSTACK_NAME_PROPERTY,
    OPENSTACK_TYPE_PROPERTY,
    USE_EXTERNAL_RESOURCE_PROPERTY,
    Config
)
from openstack_plugin_common.floatingip import IP_ADDRESS_PROPERTY

# copying openstack config by default to root since deployment
# workers use the root user.
OPENSTACK_CONFIG_PATH_DEFAULT_PATH = '/root/openstack_config.json'
PROVIDER_CONTEXT_RUNTIME_PROPERTY = 'provider_context'


def configure(openstack_config):
    _set_provider_context()
    _copy_openstack_configuration_to_manager(openstack_config)


def _copy_openstack_configuration_to_manager(openstack_config):
    merged_config = Config().get()
    Config.update_config(merged_config, openstack_config)

    config_path = ctx.node.properties.get(
        'cloudify').get(
        'plugins').get(
        'openstack_config_path') or OPENSTACK_CONFIG_PATH_DEFAULT_PATH

    tmp = tempfile.mktemp()
    with open(tmp, 'w') as f:
        json.dump(merged_config, f)

    fabric.api.sudo('mkdir -p {0}'.format(os.path.dirname(config_path)))
    fabric.api.put(tmp, '{0}'.format(config_path), use_sudo=True)


def _set_provider_context():
    # Do not use this code section as a reference - it is a workaround for a
    #  deprecated feature and will be removed in the near future

    resources = dict()

    # the reference to storage only works the workflow is executed as a
    # local workflow (i.e. in a local environment context)
    node_instances = ctx._endpoint.storage.get_node_instances()
    nodes_by_id = \
        {node.id: node for node in ctx._endpoint.storage.get_nodes()}

    node_id_to_provider_context_field = {
        'management_subnet': 'subnet',
        'management_network': 'int_network',
        'router': 'router',
        'agents_security_group': 'agents_security_group',
        'management_security_group': 'management_security_group',
        'manager_server_ip': 'floating_ip',
        'external_network': 'ext_network',
        'manager_server': 'management_server',
        'management_keypair': 'management_keypair',
        'agent_keypair': 'agents_keypair'
    }
    for node_instance in node_instances:
        if node_instance.node_id in node_id_to_provider_context_field:
            run_props = node_instance.runtime_properties
            props = nodes_by_id[node_instance.node_id].properties
            provider_context_field = \
                node_id_to_provider_context_field[node_instance.node_id]
            resources[provider_context_field] = {
                'external_resource': props[USE_EXTERNAL_RESOURCE_PROPERTY],
                'type': run_props[OPENSTACK_TYPE_PROPERTY],
                'id': run_props[OPENSTACK_ID_PROPERTY]}
            if node_instance.node_id == 'manager_server_ip':
                resources[provider_context_field]['ip'] = \
                    run_props[IP_ADDRESS_PROPERTY]
            else:
                resources[provider_context_field]['name'] = \
                    run_props[OPENSTACK_NAME_PROPERTY]

    provider = {
        'resources': resources
    }

    ctx.instance.runtime_properties[PROVIDER_CONTEXT_RUNTIME_PROPERTY] = \
        provider
