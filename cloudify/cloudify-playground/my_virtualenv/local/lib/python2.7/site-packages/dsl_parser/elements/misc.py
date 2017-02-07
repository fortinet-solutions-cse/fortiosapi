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

from dsl_parser import elements
from dsl_parser.elements import (
    data_types,
    version as element_version)
from dsl_parser.framework.elements import (DictElement,
                                           Element,
                                           Leaf,
                                           Dict)


class OutputDescription(Element):

    schema = Leaf(type=str)


class OutputValue(Element):

    required = True
    schema = Leaf(type=elements.PRIMITIVE_TYPES)


class Output(Element):

    schema = {
        'description': OutputDescription,
        'value': OutputValue
    }


class Outputs(DictElement):

    schema = Dict(type=Output)


class Inputs(data_types.Schema):
    pass


class DSLDefinitions(Element):

    schema = Leaf(type=[dict, list])
    requires = {
        element_version.ToscaDefinitionsVersion: ['version'],
        'inputs': ['validate_version']
    }

    def validate(self, version, validate_version):
        if validate_version:
            self.validate_version(version, (1, 2))


class Description(Element):

    schema = Leaf(type=str)

    requires = {
        element_version.ToscaDefinitionsVersion: ['version'],
        'inputs': ['validate_version']
    }

    def validate(self, version, validate_version):
        if validate_version:
            self.validate_version(version, (1, 2))
