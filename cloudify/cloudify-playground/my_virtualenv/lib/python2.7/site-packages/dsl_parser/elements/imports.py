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

import os
import urllib

import networkx as nx

from dsl_parser import (exceptions,
                        constants,
                        version as _version,
                        utils)
from dsl_parser.framework.elements import (Element,
                                           Leaf,
                                           List)


MERGE_NO_OVERRIDE = set([
    constants.INTERFACES,
    constants.NODE_TYPES,
    constants.PLUGINS,
    constants.WORKFLOWS,
    constants.RELATIONSHIPS,
    constants.POLICY_TYPES,
    constants.GROUPS,
    constants.POLICY_TRIGGERS,
    constants.DATA_TYPES])

MERGEABLE_FROM_DSL_VERSION_1_3 = [
    constants.INPUTS,
    constants.OUTPUTS,
    constants.NODE_TEMPLATES
]

IGNORE = set([
    constants.DSL_DEFINITIONS,
    constants.IMPORTS,
    _version.VERSION
])


class Import(Element):

    schema = Leaf(type=str)


class Imports(Element):

    schema = List(type=Import)


class ImportLoader(Element):

    schema = Leaf(type=str)


class ImportsLoader(Element):

    schema = List(type=ImportLoader)
    provides = ['resource_base']
    requires = {
        'inputs': ['main_blueprint_holder',
                   'resources_base_url',
                   'blueprint_location',
                   'version',
                   'resolver',
                   'validate_version']
    }

    resource_base = None

    def validate(self, **kwargs):
        imports = [i.value for i in self.children()]
        imports_set = set()
        for _import in imports:
            if _import in imports_set:
                raise exceptions.DSLParsingFormatException(
                    2, 'Duplicate imports')
            imports_set.add(_import)

    def parse(self,
              main_blueprint_holder,
              resources_base_url,
              blueprint_location,
              version,
              resolver,
              validate_version):
        if blueprint_location:
            blueprint_location = _dsl_location_to_url(
                dsl_location=blueprint_location,
                resources_base_url=resources_base_url)
            slash_index = blueprint_location.rfind('/')
            self.resource_base = blueprint_location[:slash_index]
        return _combine_imports(parsed_dsl_holder=main_blueprint_holder,
                                dsl_location=blueprint_location,
                                resources_base_url=resources_base_url,
                                version=version,
                                resolver=resolver,
                                validate_version=validate_version)

    def calculate_provided(self, **kwargs):
        return {
            'resource_base': self.resource_base
        }


def _dsl_location_to_url(dsl_location, resources_base_url):
    if dsl_location is not None:
        dsl_location = _get_resource_location(dsl_location, resources_base_url)
        if dsl_location is None:
            ex = exceptions.DSLParsingLogicException(
                30, "Failed converting dsl "
                    "location to url: no suitable "
                    "location found "
                    "for dsl '{0}'"
                    .format(dsl_location))
            ex.failed_import = dsl_location
            raise ex
    return dsl_location


def _get_resource_location(resource_name,
                           resources_base_url,
                           current_resource_context=None):
    url_parts = resource_name.split(':')
    if url_parts[0] in ['http', 'https', 'file', 'ftp']:
        return resource_name

    if os.path.exists(resource_name):
        return 'file:{0}'.format(
            urllib.pathname2url(os.path.abspath(resource_name)))

    if current_resource_context:
        candidate_url = current_resource_context[
            :current_resource_context.rfind('/') + 1] + resource_name
        if utils.url_exists(candidate_url):
            return candidate_url

    if resources_base_url:
        return resources_base_url + resource_name

    return None


def _combine_imports(parsed_dsl_holder, dsl_location,
                     resources_base_url, version, resolver,
                     validate_version):
    ordered_imports = _build_ordered_imports(parsed_dsl_holder,
                                             dsl_location,
                                             resources_base_url,
                                             resolver)
    holder_result = parsed_dsl_holder.copy()
    version_key_holder, version_value_holder = parsed_dsl_holder.get_item(
        _version.VERSION)
    holder_result.value = {}
    for imported in ordered_imports:
        import_url = imported['import']
        parsed_imported_dsl_holder = imported['parsed']
        if validate_version:
            _validate_version(version.raw, import_url,
                              parsed_imported_dsl_holder)
        _merge_parsed_into_combined(
            holder_result, parsed_imported_dsl_holder, version)
    holder_result.value[version_key_holder] = version_value_holder
    return holder_result


def _build_ordered_imports(parsed_dsl_holder,
                           dsl_location,
                           resources_base_url,
                           resolver):

    def location(value):
        return value or 'root'

    imports_graph = ImportsGraph()
    imports_graph.add(location(dsl_location), parsed_dsl_holder)

    def _build_ordered_imports_recursive(_current_parsed_dsl_holder,
                                         _current_import):
        imports_key_holder, imports_value_holder = _current_parsed_dsl_holder.\
            get_item(constants.IMPORTS)
        if not imports_value_holder:
            return

        for another_import in imports_value_holder.restore():
            import_url = _get_resource_location(another_import,
                                                resources_base_url,
                                                _current_import)
            if import_url is None:
                ex = exceptions.DSLParsingLogicException(
                    13, "Import failed: no suitable location found for "
                        "import '{0}'".format(another_import))
                ex.failed_import = another_import
                raise ex
            if import_url in imports_graph:
                imports_graph.add_graph_dependency(import_url,
                                                   location(_current_import))
            else:
                raw_imported_dsl = resolver.fetch_import(import_url)
                imported_dsl_holder = utils.load_yaml(
                    raw_yaml=raw_imported_dsl,
                    error_message="Failed to parse import '{0}' (via '{1}')"
                                  .format(another_import, import_url),
                    filename=another_import)
                imports_graph.add(import_url, imported_dsl_holder,
                                  location(_current_import))
                _build_ordered_imports_recursive(imported_dsl_holder,
                                                 import_url)
    _build_ordered_imports_recursive(parsed_dsl_holder, dsl_location)
    return imports_graph.topological_sort()


def _validate_version(dsl_version,
                      import_url,
                      parsed_imported_dsl_holder):
    version_key_holder, version_value_holder = parsed_imported_dsl_holder\
        .get_item(_version.VERSION)
    if version_value_holder and version_value_holder.value != dsl_version:
        raise exceptions.DSLParsingLogicException(
            28, "An import uses a different "
                "tosca_definitions_version than the one defined in "
                "the main blueprint's file: main blueprint's file "
                "version is '{0}', import with different version is "
                "'{1}', version of problematic import is '{2}'"
                .format(dsl_version,
                        import_url,
                        version_value_holder.value))


def _merge_parsed_into_combined(combined_parsed_dsl_holder,
                                parsed_imported_dsl_holder,
                                version):
    merge_no_override = MERGE_NO_OVERRIDE.copy()
    if version['definitions_version'] > (1, 2):
        merge_no_override.update(MERGEABLE_FROM_DSL_VERSION_1_3)
    for key_holder, value_holder in parsed_imported_dsl_holder.value.\
            iteritems():
        if key_holder.value in IGNORE:
            pass
        elif key_holder.value not in combined_parsed_dsl_holder:
            combined_parsed_dsl_holder.value[key_holder] = value_holder
        elif key_holder.value in merge_no_override:
            _, to_dict = combined_parsed_dsl_holder.get_item(key_holder.value)
            _merge_into_dict_or_throw_on_duplicate(
                from_dict_holder=value_holder,
                to_dict_holder=to_dict,
                key_name=key_holder.value)
        else:
            if key_holder.value in MERGEABLE_FROM_DSL_VERSION_1_3:
                msg = ("Import failed: non-mergeable field: '{0}'. "
                       "{0} can be imported multiple times only from "
                       "cloudify_dsl_1_3 and above.")
            else:
                msg = "Import failed: non-mergeable field: '{0}'"
            raise exceptions.DSLParsingLogicException(
                3, msg.format(key_holder.value))


def _merge_into_dict_or_throw_on_duplicate(from_dict_holder, to_dict_holder,
                                           key_name):
    for key_holder, value_holder in from_dict_holder.value.iteritems():
        if key_holder.value not in to_dict_holder:
            to_dict_holder.value[key_holder] = value_holder
        else:
            raise exceptions.DSLParsingLogicException(
                4, "Import failed: Could not merge '{0}' due to conflict "
                   "on '{1}'".format(key_name, key_holder.value))


class ImportsGraph(object):

    def __init__(self):
        self._imports_tree = nx.DiGraph()
        self._imports_graph = nx.DiGraph()

    def add(self, import_url, parsed, via_import=None):
        if import_url not in self._imports_tree:
            self._imports_tree.add_node(import_url, parsed=parsed)
            self._imports_graph.add_node(import_url, parsed=parsed)
        if via_import:
            self._imports_tree.add_edge(import_url, via_import)
            self._imports_graph.add_edge(import_url, via_import)

    def add_graph_dependency(self, import_url, via_import):
        if via_import:
            self._imports_graph.add_edge(import_url, via_import)

    def topological_sort(self):
        return reversed(list(
            ({'import': i,
             'parsed': self._imports_tree.node[i]['parsed']}
             for i in nx.topological_sort(self._imports_tree))))

    def __contains__(self, item):
        return item in self._imports_tree
