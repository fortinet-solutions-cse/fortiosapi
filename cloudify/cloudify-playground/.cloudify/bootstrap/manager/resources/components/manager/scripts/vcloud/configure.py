# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tempfile
import json

import fabric

import vcloud_plugin_common
from cloudify import ctx

PROVIDER_CONTEXT_RUNTIME_PROPERTY = 'provider_context'


def configure(vcloud_config):
    """copy current configs to manager node

    copy vcloud configuration to managment host,
    and save current context to .cloudify/context
    For now - we have saved only managment network name
    """
    _copy_vcloud_configuration_to_manager(vcloud_config)
    _save_context()


def _copy_vcloud_configuration_to_manager(vcloud_config):
    """
        Copy current config to remote node
    """
    tmp = tempfile.mktemp()
    with open(tmp, 'w') as f:
        json.dump(vcloud_config, f)
    fabric.api.put(tmp,
                   vcloud_plugin_common.Config.VCLOUD_CONFIG_PATH_DEFAULT)


def _save_context():
    """
        save current managment network for use as default network for
        all new nodes
    """
    resources = dict()

    node_instances = ctx._endpoint.storage.get_node_instances()
    nodes_by_id = \
        {node.id: node for node in ctx._endpoint.storage.get_nodes()}

    for node_instance in node_instances:
        props = nodes_by_id[node_instance.node_id].properties

        if "management_network" == node_instance.node_id:
            resources['int_network'] = {
                "name": props.get('resource_id')
            }

    provider = {
        'resources': resources
    }

    ctx.instance.runtime_properties[PROVIDER_CONTEXT_RUNTIME_PROPERTY] = \
        provider
