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

import copy

from dsl_parser import (functions,
                        exceptions,
                        scan,
                        models,
                        parser,
                        multi_instance)
from dsl_parser.multi_instance import modify_deployment


__all__ = [
    'modify_deployment'
]


def parse_dsl(dsl_location,
              resources_base_url,
              resolver=None,
              validate_version=True,
              additional_resources=()):
    return parser.parse_from_url(
            dsl_url=dsl_location,
            resources_base_url=resources_base_url,
            resolver=resolver,
            validate_version=validate_version,
            additional_resource_sources=additional_resources)


def _set_plan_inputs(plan, inputs=None):
    inputs = inputs if inputs else {}
    # Verify inputs satisfied
    missing_inputs = []
    for input_name, input_def in plan['inputs'].iteritems():
        if input_name not in inputs:
            if 'default' in input_def and input_def['default'] is not None:
                inputs[input_name] = input_def['default']
            else:
                missing_inputs.append(input_name)

    if missing_inputs:
        raise exceptions.MissingRequiredInputError(
            "Required inputs {0} were not specified - expected "
            "inputs: {1}".format(missing_inputs, plan['inputs'].keys())
        )
    # Verify all inputs appear in plan
    not_expected = [input_name for input_name in inputs.keys()
                    if input_name not in plan['inputs']]
    if not_expected:
        raise exceptions.UnknownInputError(
            "Unknown inputs {0} specified - "
            "expected inputs: {1}".format(not_expected,
                                          plan['inputs'].keys()))

    plan['inputs'] = inputs


def _process_functions(plan):
    handler = functions.plan_evaluation_handler(plan)
    scan.scan_service_template(plan, handler, replace=True)


def prepare_deployment_plan(plan, inputs=None, **kwargs):
    """
    Prepare a plan for deployment
    """
    plan = models.Plan(copy.deepcopy(plan))
    _set_plan_inputs(plan, inputs)
    _process_functions(plan)
    return multi_instance.create_deployment_plan(plan)
