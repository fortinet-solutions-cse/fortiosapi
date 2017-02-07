########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
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

import contextlib
import urllib2

from dsl_parser import (functions,
                        utils)
from dsl_parser.framework import parser
from dsl_parser.elements import blueprint
from dsl_parser.import_resolver.default_import_resolver import \
    DefaultImportResolver


def parse_from_path(dsl_file_path,
                    resources_base_url=None,
                    resolver=None,
                    validate_version=True,
                    additional_resource_sources=()):
    with open(dsl_file_path, 'r') as f:
        dsl_string = f.read()
    return _parse(dsl_string,
                  resources_base_url=resources_base_url,
                  dsl_location=dsl_file_path,
                  resolver=resolver,
                  validate_version=validate_version,
                  additional_resource_sources=additional_resource_sources)


def parse_from_url(dsl_url,
                   resources_base_url=None,
                   resolver=None,
                   validate_version=True,
                   additional_resource_sources=()):
    try:
        with contextlib.closing(urllib2.urlopen(dsl_url)) as f:
            dsl_string = f.read()
    except urllib2.HTTPError as e:
        if e.code == 404:
            # HTTPError.__str__ uses the 'msg'.
            # by default it is set to 'Not Found' for 404 errors, which is not
            # very helpful, so we override it with a more meaningful message
            # that specifies the missing url.
            e.msg = '{0} not found'.format(e.filename)
        raise
    return _parse(dsl_string,
                  resources_base_url=resources_base_url,
                  dsl_location=dsl_url,
                  resolver=resolver,
                  validate_version=validate_version,
                  additional_resource_sources=additional_resource_sources)


def parse(dsl_string,
          resources_base_url=None,
          resolver=None,
          validate_version=True):
    return _parse(dsl_string,
                  resources_base_url=resources_base_url,
                  resolver=resolver,
                  validate_version=validate_version)


def _parse(dsl_string,
           resources_base_url,
           dsl_location=None,
           resolver=None,
           validate_version=True,
           additional_resource_sources=()):
    parsed_dsl_holder = utils.load_yaml(raw_yaml=dsl_string,
                                        error_message='Failed to parse DSL',
                                        filename=dsl_location)

    if not resolver:
        resolver = DefaultImportResolver()

    # validate version schema and extract actual version used
    result = parser.parse(
        parsed_dsl_holder,
        element_cls=blueprint.BlueprintVersionExtractor,
        inputs={
            'validate_version': validate_version
        },
        strict=False)
    version = result['plan_version']

    # handle imports
    result = parser.parse(
        value=parsed_dsl_holder,
        inputs={
            'main_blueprint_holder': parsed_dsl_holder,
            'resources_base_url': resources_base_url,
            'blueprint_location': dsl_location,
            'version': version,
            'resolver': resolver,
            'validate_version': validate_version
        },
        element_cls=blueprint.BlueprintImporter,
        strict=False)
    resource_base = [result['resource_base']]
    if additional_resource_sources:
        resource_base.extend(additional_resource_sources)

    merged_blueprint_holder = result['merged_blueprint']

    # parse blueprint
    plan = parser.parse(
        value=merged_blueprint_holder,
        inputs={
            'resource_base': resource_base,
            'validate_version': validate_version
        },
        element_cls=blueprint.Blueprint)

    functions.validate_functions(plan)
    return plan
