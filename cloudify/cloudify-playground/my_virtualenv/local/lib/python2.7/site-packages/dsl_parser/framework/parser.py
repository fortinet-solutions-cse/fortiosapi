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

import networkx as nx

from dsl_parser import exceptions
from dsl_parser.framework import elements
from dsl_parser.framework.requirements import Requirement


class SchemaAPIValidator(object):

    def validate(self, element_cls):
        self._traverse_element_cls(element_cls)

    def _traverse_element_cls(self, element_cls):
        try:
            if not issubclass(element_cls, elements.Element):
                raise exceptions.DSLParsingSchemaAPIException(1)
        except TypeError:
            raise exceptions.DSLParsingSchemaAPIException(1)
        self._traverse_schema(element_cls.schema)

    def _traverse_schema(self, schema, list_nesting=0):
        if isinstance(schema, dict):
            for key, value in schema.items():
                if not isinstance(key, basestring):
                    raise exceptions.DSLParsingSchemaAPIException(1)
                self._traverse_element_cls(value)
        elif isinstance(schema, list):
            if list_nesting > 0:
                raise exceptions.DSLParsingSchemaAPIException(1)
            if len(schema) == 0:
                raise exceptions.DSLParsingSchemaAPIException(1)
            for value in schema:
                self._traverse_schema(value, list_nesting+1)
        elif isinstance(schema, elements.ElementType):
            if isinstance(schema, elements.Leaf):
                if not isinstance(schema.type, (type, list, tuple)):
                    raise exceptions.DSLParsingSchemaAPIException(1)
                if (isinstance(schema.type, (list, tuple)) and
                    (not schema.type or
                     not all([isinstance(i, type) for i in schema.type]))):
                    raise exceptions.DSLParsingSchemaAPIException(1)
            elif isinstance(schema, elements.Dict):
                self._traverse_element_cls(schema.type)
            elif isinstance(schema, elements.List):
                self._traverse_element_cls(schema.type)
            else:
                raise exceptions.DSLParsingSchemaAPIException(1)
        else:
            raise exceptions.DSLParsingSchemaAPIException(1)
_schema_validator = SchemaAPIValidator()


class Context(object):

    def __init__(self,
                 value,
                 element_cls,
                 element_name,
                 inputs):
        self.inputs = inputs or {}
        self.element_type_to_elements = {}
        self._root_element = None
        self._element_tree = nx.DiGraph()
        self._element_graph = nx.DiGraph()
        self._traverse_element_cls(element_cls=element_cls,
                                   name=element_name,
                                   value=value,
                                   parent_element=None)
        self._calculate_element_graph()

    @property
    def parsed_value(self):
        return self._root_element.value if self._root_element else None

    def child_elements_iter(self, element):
        return self._element_tree.successors_iter(element)

    def ancestors_iter(self, element):
        current_element = element
        while True:
            predecessors = self._element_tree.predecessors(current_element)
            if not predecessors:
                return
            if len(predecessors) > 1:
                raise exceptions.DSLParsingFormatException(
                    1, 'More than 1 parent found for {0}'
                       .format(element))
            current_element = predecessors[0]
            yield current_element

    def descendants(self, element):
        return nx.descendants(self._element_tree, element)

    def _add_element(self, element, parent=None):
        element_type = type(element)
        if element_type not in self.element_type_to_elements:
            self.element_type_to_elements[element_type] = []
        self.element_type_to_elements[element_type].append(element)

        self._element_tree.add_node(element)
        if parent:
            self._element_tree.add_edge(parent, element)
        else:
            self._root_element = element

    def _traverse_element_cls(self,
                              element_cls,
                              name,
                              value,
                              parent_element):
        element = element_cls(name=name,
                              initial_value=value,
                              context=self)
        self._add_element(element, parent=parent_element)
        self._traverse_schema(schema=element_cls.schema,
                              parent_element=element)

    def _traverse_schema(self, schema, parent_element):
        if isinstance(schema, dict):
            self._traverse_dict_schema(schema=schema,
                                       parent_element=parent_element)
        elif isinstance(schema, elements.ElementType):
            self._traverse_element_type_schema(
                schema=schema,
                parent_element=parent_element)
        elif isinstance(schema, list):
            self._traverse_list_schema(schema=schema,
                                       parent_element=parent_element)
        elif isinstance(schema, elements.UnknownSchema):
            pass
        else:
            raise ValueError('Illegal state should have been identified'
                             ' by schema API validation')

    def _traverse_dict_schema(self, schema,  parent_element):
        if not isinstance(parent_element.initial_value, dict):
            return

        parsed_names = set()
        for name, element_cls in schema.items():
            if name not in parent_element.initial_value_holder:
                value = None
            else:
                name, value = \
                    parent_element.initial_value_holder.get_item(name)
                parsed_names.add(name.value)
            self._traverse_element_cls(element_cls=element_cls,
                                       name=name,
                                       value=value,
                                       parent_element=parent_element)
        for k_holder, v_holder in parent_element.initial_value_holder.value.\
                iteritems():
            if k_holder.value not in parsed_names:
                self._traverse_element_cls(element_cls=elements.UnknownElement,
                                           name=k_holder, value=v_holder,
                                           parent_element=parent_element)

    def _traverse_element_type_schema(self, schema, parent_element):
        if isinstance(schema, elements.Leaf):
            return

        element_cls = schema.type
        if isinstance(schema, elements.Dict):
            if not isinstance(parent_element.initial_value, dict):
                return
            for name_holder, value_holder in parent_element.\
                    initial_value_holder.value.items():
                self._traverse_element_cls(element_cls=element_cls,
                                           name=name_holder,
                                           value=value_holder,
                                           parent_element=parent_element)
        elif isinstance(schema, elements.List):
            if not isinstance(parent_element.initial_value, list):
                return
            for index, value_holder in enumerate(
                    parent_element.initial_value_holder.value):
                self._traverse_element_cls(element_cls=element_cls,
                                           name=index,
                                           value=value_holder,
                                           parent_element=parent_element)
        else:
            raise ValueError('Illegal state should have been identified'
                             ' by schema API validation')

    def _traverse_list_schema(self, schema, parent_element):
        for schema_item in schema:
            self._traverse_schema(schema=schema_item,
                                  parent_element=parent_element)

    def _calculate_element_graph(self):
        self.element_graph = nx.DiGraph(self._element_tree)
        for element_type, _elements in self.element_type_to_elements.items():
            requires = element_type.requires
            for requirement, requirement_values in requires.items():
                requirement_values = [
                    Requirement(r) if isinstance(r, basestring)
                    else r for r in requirement_values]
                if requirement == 'inputs':
                    continue
                if requirement == 'self':
                    requirement = element_type
                dependencies = self.element_type_to_elements.get(
                    requirement, [])
                for dependency in dependencies:
                    for element in _elements:
                        predicates = [r.predicate for r in requirement_values
                                      if r.predicate is not None]
                        add_dependency = not predicates or all([
                            predicate(element, dependency)
                            for predicate in predicates])
                        if add_dependency:
                            self.element_graph.add_edge(element, dependency)
        # we reverse the graph because only netorkx 1.9.1 has the reverse
        # flag in the topological sort function, it is only used by it
        # so this should be good
        self.element_graph.reverse(copy=False)

    def elements_graph_topological_sort(self):
        try:
            return nx.topological_sort(self.element_graph)
        except nx.NetworkXUnfeasible:
            # Cycle detected
            cycle = nx.recursive_simple_cycles(self.element_graph)[0]
            names = [str(e.name) for e in cycle]
            names.append(str(names[0]))
            ex = exceptions.DSLParsingLogicException(
                exceptions.ERROR_CODE_CYCLE,
                'Parsing failed. Circular dependency detected: {0}'
                .format(' --> '.join(names)))
            ex.circular_dependency = names
            raise ex


class Parser(object):

    def parse(self,
              value,
              element_cls,
              element_name='root',
              inputs=None,
              strict=True):
        context = Context(
            value=value,
            element_cls=element_cls,
            element_name=element_name,
            inputs=inputs)
        for element in context.elements_graph_topological_sort():
            try:
                self._validate_element_schema(element, strict=strict)
                self._process_element(element)
            except exceptions.DSLParsingException as e:
                if not e.element:
                    e.element = element
                raise
        return context.parsed_value

    @staticmethod
    def _validate_element_schema(element, strict):
        value = element.initial_value
        if element.required and value is None:
            raise exceptions.DSLParsingFormatException(
                1, "'{0}' key is required but it is currently missing"
                   .format(element.name))

        def validate_schema(schema):
            if isinstance(schema, (dict, elements.Dict)):
                if not isinstance(value, dict):
                    raise exceptions.DSLParsingFormatException(
                        1, _expected_type_message(value, dict))
                for key in value.keys():
                    if not isinstance(key, basestring):
                        raise exceptions.DSLParsingFormatException(
                            1, "Dict keys must be strings but"
                               " found '{0}' of type '{1}'"
                               .format(key, _py_type_to_user_type(type(key))))

            if strict and isinstance(schema, dict):
                for key in value.keys():
                    if key not in schema:
                        ex = exceptions.DSLParsingFormatException(
                            1, "'{0}' is not in schema. "
                               "Valid schema values: {1}"
                               .format(key, schema.keys()))
                        for child_element in element.children():
                            if child_element.name == key:
                                ex.element = child_element
                                break
                        raise ex

            if (isinstance(schema, elements.List) and
                    not isinstance(value, list)):
                raise exceptions.DSLParsingFormatException(
                    1, _expected_type_message(value, list))

            if (isinstance(schema, elements.Leaf) and
                    not isinstance(value, schema.type)):
                raise exceptions.DSLParsingFormatException(
                    1, _expected_type_message(value, schema.type))
        if value is not None:
            if isinstance(element.schema, list):
                validated = False
                last_error = None
                for schema_item in element.schema:
                    try:
                        validate_schema(schema_item)
                    except exceptions.DSLParsingFormatException as e:
                        last_error = e
                    else:
                        validated = True
                        break
                if not validated:
                    if not last_error:
                        raise ValueError('Illegal state should have been '
                                         'identified by schema API validation')
                    else:
                        raise last_error
            else:
                validate_schema(element.schema)

    def _process_element(self, element):
        required_args = self._extract_element_requirements(element)
        element.validate(**required_args)
        element.value = element.parse(**required_args)
        element.provided = element.calculate_provided(**required_args)

    @staticmethod
    def _extract_element_requirements(element):
        context = element.context
        required_args = {}
        for required_type, requirements in element.requires.items():
            requirements = [Requirement(r) if isinstance(r, basestring)
                            else r for r in requirements]
            if not requirements:
                # only set required type as a logical dependency
                pass
            elif required_type == 'inputs':
                for input in requirements:
                    if input.name not in context.inputs and input.required:
                        raise exceptions.DSLParsingFormatException(
                            1, "Missing required input '{0}'. "
                               "Existing inputs: "
                               .format(input.name, context.inputs.keys()))
                    required_args[input.name] = context.inputs.get(input.name)
            else:
                if required_type == 'self':
                    required_type = type(element)
                required_type_elements = context.element_type_to_elements.get(
                    required_type, [])
                for requirement in requirements:
                    result = []
                    for required_element in required_type_elements:
                        if requirement.predicate and not requirement.predicate(
                                element, required_element):
                            continue
                        if requirement.parsed:
                            result.append(required_element.value)
                        else:
                            if (requirement.name not in
                                    required_element.provided):
                                provided = required_element.provided.keys()
                                if requirement.required:
                                    raise exceptions.DSLParsingFormatException(
                                        1,
                                        "Required value '{0}' is not "
                                        "provided by '{1}'. Provided values "
                                        "are: {2}"
                                        .format(requirement.name,
                                                required_element.name,
                                                provided))
                                else:
                                    continue
                            result.append(required_element.provided[
                                requirement.name])

                    if len(result) != 1 and not requirement.multiple_results:
                        if requirement.required:
                            raise exceptions.DSLParsingFormatException(
                                1, "Expected exactly one result for "
                                   "requirement '{0}' but found {1}"
                                   .format(requirement.name,
                                           'none' if not result else result))
                        elif not result:
                            result = [None]
                        else:
                            raise ValueError('Illegal state')

                    if not requirement.multiple_results:
                        result = result[0]
                    required_args[requirement.name] = result

        return required_args
_parser = Parser()


def validate_schema_api(element_cls):
    _schema_validator.validate(element_cls)


def parse(value,
          element_cls,
          element_name='root',
          inputs=None,
          strict=True):
    validate_schema_api(element_cls)
    return _parser.parse(value=value,
                         element_cls=element_cls,
                         element_name=element_name,
                         inputs=inputs,
                         strict=strict)


def _expected_type_message(value, expected_type):
    return ("Expected '{0}' type but found '{1}' type"
            .format(_py_type_to_user_type(expected_type),
                    _py_type_to_user_type(type(value))))


def _py_type_to_user_type(_type):
    if isinstance(_type, tuple):
        return list(set(_py_type_to_user_type(t) for t in _type))
    elif issubclass(_type, basestring):
        return 'string'
    elif issubclass(_type, bool):
        return 'boolean'
    elif issubclass(_type, int) or issubclass(_type, long):
        return 'integer'
    elif issubclass(_type, float):
        return 'float'
    elif issubclass(_type, dict):
        return 'dict'
    elif issubclass(_type, list):
        return 'list'
    else:
        raise ValueError('Unexpected type: {0}'.format(_type))
