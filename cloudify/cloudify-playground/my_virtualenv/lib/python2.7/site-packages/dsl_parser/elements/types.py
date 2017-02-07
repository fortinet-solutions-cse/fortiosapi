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

from dsl_parser import exceptions
from dsl_parser.framework.elements import (DictElement,
                                           Element,
                                           Leaf)


class Types(DictElement):
    pass


class Type(Element):

    def create_type_hierarchy(self, super_type):
        if super_type:
            type_hierarchy = super_type['type_hierarchy'][:]
        else:
            type_hierarchy = []
        type_hierarchy.append(self.name)
        return type_hierarchy

    @staticmethod
    def fix_properties(value):
        for key, value in value['properties'].iteritems():
            value.pop('initial_default', None)


class DerivedFrom(Element):

    schema = Leaf(type=str)
    descriptor = ''

    def validate(self):
        if self.initial_value is None:
            return

        if self.initial_value not in self.ancestor(Types).initial_value:
            raise exceptions.DSLParsingLogicException(
                exceptions.ERROR_UNKNOWN_TYPE,
                "Missing definition for {0} '{1}' which is declared as "
                "derived by {0} '{2}'"
                .format(self.descriptor,
                        self.initial_value,
                        self.ancestor(Type).name))


class RelationshipDerivedFrom(DerivedFrom):

    descriptor = 'relationship'


class TypeDerivedFrom(DerivedFrom):

    descriptor = 'type'


class DataTypeDerivedFrom(DerivedFrom):

    descriptor = 'data type'


def derived_from_predicate(source, target):
    try:
        derived_from = source.child(DerivedFrom).initial_value
        return derived_from and derived_from == target.name
    except exceptions.DSLParsingElementMatchException:
        return False
