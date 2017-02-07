########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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


from dsl_parser import (constants,
                        utils)
from dsl_parser.interfaces import interfaces_parser
from dsl_parser.elements import (operation,
                                 data_types as _data_types,
                                 types)
from dsl_parser.framework import requirements
from dsl_parser.framework.elements import Dict


class NodeType(types.Type):

    schema = {
        'derived_from': types.TypeDerivedFrom,
        'interfaces': operation.NodeTypeInterfaces,
        'properties': _data_types.SchemaWithInitialDefault,
    }
    requires = {
        'self': [requirements.Value('super_type',
                                    predicate=types.derived_from_predicate,
                                    required=False)],
        _data_types.DataTypes: [requirements.Value('data_types')]
    }

    def parse(self, super_type, data_types):
        node_type = self.build_dict_result()
        if not node_type.get('derived_from'):
            node_type.pop('derived_from', None)
        if super_type:
            node_type[constants.PROPERTIES] = utils.merge_schemas(
                overridden_schema=super_type.get('properties', {}),
                overriding_schema=node_type.get('properties', {}),
                data_types=data_types)
            node_type[constants.INTERFACES] = interfaces_parser. \
                merge_node_type_interfaces(
                    overridden_interfaces=super_type[constants.INTERFACES],
                    overriding_interfaces=node_type[constants.INTERFACES])
        node_type[constants.TYPE_HIERARCHY] = self.create_type_hierarchy(
            super_type)
        self.fix_properties(node_type)
        return node_type


class NodeTypes(types.Types):

    schema = Dict(type=NodeType)
    provides = ['host_types']

    def calculate_provided(self):
        return {
            'host_types': self._types_derived_from(constants.HOST_TYPE)
        }

    def _types_derived_from(self, derived_from):
        return set(type_name for type_name, _type in self.value.items()
                   if derived_from in _type[constants.TYPE_HIERARCHY])
