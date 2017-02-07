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

import copy
import contextlib
import importlib
import urllib2
import sys

import yaml.parser

from dsl_parser import yaml_loader
from dsl_parser import functions
from dsl_parser import constants
from dsl_parser.constants import RESOLVER_IMPLEMENTATION_KEY, \
    RESLOVER_PARAMETERS_KEY
from dsl_parser import exceptions
from dsl_parser.exceptions import (DSLParsingLogicException,
                                   DSLParsingFormatException)
from dsl_parser.import_resolver.default_import_resolver import \
    DefaultImportResolver


class ResolverInstantiationError(Exception):
    pass


def merge_schemas(overridden_schema,
                  overriding_schema,
                  data_types):
    merged = overriding_schema.copy()
    for key, overridden_property in overridden_schema.items():
        if key not in overriding_schema:
            merged[key] = overridden_property
        else:
            overriding_property = overriding_schema[key]
            overriding_type = overriding_property.get('type')
            overridden_type = overridden_property.get('type')
            overridden_default = overridden_property.get('default')
            overriding_initial_default = overriding_property.get(
                'initial_default')
            if (overriding_type is not None and
                overriding_type == overridden_type and
                overriding_type in data_types and
                overriding_type not in constants.USER_PRIMITIVE_TYPES and
                    overridden_default is not None):
                if overriding_initial_default is None:
                    overriding_initial_default = {}
                default_value = parse_value(
                    value=overriding_initial_default,
                    derived_value=overridden_default,
                    type_name=overridden_type,
                    data_types=data_types,
                    undefined_property_error_message='illegal state',
                    missing_property_error_message='illegal state',
                    node_name='illegal state',
                    path=[],
                    raise_on_missing_property=False)
                if default_value:
                    merged[key]['default'] = default_value
    return merged


def flatten_schema(schema):
    flattened_schema_props = {}
    for prop_key, prop in schema.iteritems():
        if 'default' in prop:
            flattened_schema_props[prop_key] = prop['default']
    return flattened_schema_props


def _property_description(path, name=None):
    if not path:
        return name
    if name is not None:
        path = copy.copy(path)
        path.append(name)
    return '.'.join(path)


def merge_schema_and_instance_properties(
        instance_properties,
        schema_properties,
        data_types,
        undefined_property_error_message,
        missing_property_error_message,
        node_name,
        path=None,
        raise_on_missing_property=True):
    flattened_schema_props = flatten_schema(schema_properties)
    return _merge_flattened_schema_and_instance_properties(
        instance_properties=instance_properties,
        schema_properties=schema_properties,
        flattened_schema_properties=flattened_schema_props,
        data_types=data_types,
        undefined_property_error_message=undefined_property_error_message,
        missing_property_error_message=missing_property_error_message,
        node_name=node_name,
        path=path,
        raise_on_missing_property=raise_on_missing_property)


def _merge_flattened_schema_and_instance_properties(
        instance_properties,
        schema_properties,
        flattened_schema_properties,
        data_types,
        undefined_property_error_message,
        missing_property_error_message,
        node_name,
        path,
        raise_on_missing_property):
    path = path or []

    # validate instance properties don't
    # contain properties that are not defined
    # in the schema.
    for key in instance_properties.iterkeys():
        if key not in schema_properties:
            ex = DSLParsingLogicException(
                106,
                undefined_property_error_message.format(
                    node_name,
                    _property_description(path, key)))
            ex.property = key
            raise ex

    merged_properties = dict(flattened_schema_properties.items() +
                             instance_properties.items())
    result = {}
    for key, property_schema in schema_properties.iteritems():
        if key not in merged_properties:
            required = property_schema.get('required', True)
            if required and raise_on_missing_property:
                ex = DSLParsingLogicException(
                    107,
                    missing_property_error_message.format(
                        node_name,
                        _property_description(path, key)))
                ex.property = key
                raise ex
            else:
                continue
        prop_path = copy.copy(path)
        prop_path.append(key)
        result[key] = parse_value(
            value=merged_properties.get(key),
            derived_value=flattened_schema_properties.get(key),
            type_name=property_schema.get('type'),
            data_types=data_types,
            undefined_property_error_message=undefined_property_error_message,
            missing_property_error_message=missing_property_error_message,
            node_name=node_name,
            path=prop_path,
            raise_on_missing_property=raise_on_missing_property)
    return result


def parse_value(
        value,
        type_name,
        data_types,
        undefined_property_error_message,
        missing_property_error_message,
        node_name,
        path,
        derived_value=None,
        raise_on_missing_property=True):
    if type_name is None:
        return value
    if functions.parse(value) != value:
        # intrinsic function - not validated at the moment
        return value
    if type_name == 'integer':
        if isinstance(value, (int, long)) and not isinstance(
                value, bool):
            return value
    elif type_name == 'float':
        if isinstance(value, (int, float, long)) and not isinstance(
                value, bool):
            return value
    elif type_name == 'boolean':
        if isinstance(value, bool):
            return value
    elif type_name == 'string':
        return value
    elif type_name in data_types:
        if isinstance(value, dict):
            data_schema = data_types[type_name]['properties']
            flattened_data_schema = flatten_schema(data_schema)
            if isinstance(derived_value, dict):
                flattened_data_schema.update(derived_value)
            undef_msg = undefined_property_error_message
            return _merge_flattened_schema_and_instance_properties(
                instance_properties=value,
                schema_properties=data_schema,
                flattened_schema_properties=flattened_data_schema,
                data_types=data_types,
                undefined_property_error_message=undef_msg,
                missing_property_error_message=missing_property_error_message,
                node_name=node_name,
                path=path,
                raise_on_missing_property=raise_on_missing_property)
    else:
        raise RuntimeError(
            "Unexpected type defined in property schema for property '{0}'"
            " - unknown type is '{1}'".format(
                _property_description(path),
                type_name))

    raise DSLParsingLogicException(
        exceptions.ERROR_VALUE_DOES_NOT_MATCH_TYPE,
        "Property type validation failed in '{0}': property "
        "'{1}' type is '{2}', yet it was assigned with the "
        "value '{3}'".format(
            node_name,
            _property_description(path),
            type_name,
            value))


def load_yaml(raw_yaml, error_message, filename=None):
    try:
        return yaml_loader.load(raw_yaml, filename)
    except yaml.parser.ParserError, ex:
        raise DSLParsingFormatException(-1, '{0}: Illegal yaml; {1}'
                                        .format(error_message, ex))


def url_exists(url):
    try:
        with contextlib.closing(urllib2.urlopen(url)):
            return True
    except urllib2.URLError:
        return False


def create_import_resolver(resolver_configuration):
    if resolver_configuration:
        resolver_class_path = resolver_configuration.get(
            RESOLVER_IMPLEMENTATION_KEY)
        parameters = resolver_configuration.get(RESLOVER_PARAMETERS_KEY, {})
        if parameters and not isinstance(parameters, dict):
            raise ResolverInstantiationError(
                'Invalid parameters supplied for the resolver ({0}): '
                'parameters must be a dictionary and not {1}'
                .format(resolver_class_path or 'DefaultImportResolver',
                        type(parameters).__name__))
        try:
            if resolver_class_path:
                # custom import resolver
                return get_class_instance(resolver_class_path, parameters)
            else:
                # default import resolver
                return DefaultImportResolver(**parameters)
        except Exception, ex:
            raise ResolverInstantiationError(
                'Failed to instantiate resolver ({0}). {1}'
                .format(resolver_class_path or 'DefaultImportResolver',
                        str(ex)))
    return DefaultImportResolver()


def get_class_instance(class_path, properties):
    """Returns an instance of a class from a string formatted as module:class
    the given *args, **kwargs are passed to the instance's __init__"""
    if not properties:
        properties = {}
    try:
        cls = get_class(class_path)
        instance = cls(**properties)
    except Exception as e:
        exc_type, exc, traceback = sys.exc_info()
        raise RuntimeError('Failed to instantiate {0}, error: {1}'
                           .format(class_path, e)), None, traceback

    return instance


def get_class(class_path):
    """Returns a class from a string formatted as module:class"""
    if not class_path:
        raise ValueError('class path is missing or empty')

    if not isinstance(class_path, basestring):
        raise ValueError('class path is not a string')

    class_path = class_path.strip()
    if ':' not in class_path or class_path.count(':') > 1:
        raise ValueError('Invalid class path, expected format: '
                         'module:class')

    class_path_parts = class_path.split(':')
    class_module_str = class_path_parts[0].strip()
    class_name = class_path_parts[1].strip()

    if not class_module_str or not class_name:
        raise ValueError('Invalid class path, expected format: '
                         'module:class')

    module = importlib.import_module(class_module_str)
    if not hasattr(module, class_name):
        raise ValueError('module {0}, does not contain class {1}'
                         .format(class_module_str, class_name))

    return getattr(module, class_name)
