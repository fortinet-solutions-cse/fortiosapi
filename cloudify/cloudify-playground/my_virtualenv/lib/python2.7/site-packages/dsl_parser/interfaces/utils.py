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


from dsl_parser import (functions,
                        utils)
from dsl_parser.exceptions import DSLParsingLogicException


def validate_missing_inputs(inputs, schema_inputs):
    """Check that all inputs defined in schema_inputs exist in inputs"""

    missing_inputs = set(schema_inputs) - set(inputs)
    if missing_inputs:
        if len(missing_inputs) == 1:
            message = "Input '{0}' is missing a value".format(
                missing_inputs.pop())
        else:
            formatted_inputs = ', '.join("'{0}'".format(input_name)
                                         for input_name in missing_inputs)
            message = "Inputs {0} are missing a value".format(formatted_inputs)

        raise DSLParsingLogicException(107, message)


def validate_inputs_types(inputs, schema_inputs):
    for input_key, _input in schema_inputs.iteritems():
        input_type = _input.get('type')
        if input_type is None:
            # no type defined - no validation
            continue
        input_val = inputs[input_key]

        if functions.parse(input_val) != input_val:
            # intrinsic function - not validated at the moment
            continue

        if input_type == 'integer':
            if isinstance(input_val, (int, long)) and not \
                    isinstance(input_val, bool):
                continue
        elif input_type == 'float':
            if isinstance(input_val, (int, float, long)) and not \
                    isinstance(input_val, bool):
                continue
        elif input_type == 'boolean':
            if isinstance(input_val, bool):
                continue
        elif input_type == 'string':
            continue
        else:
            raise DSLParsingLogicException(
                    80, "Unexpected type defined in inputs schema "
                        "for input '{0}' - unknown type is {1}"
                        .format(input_key, input_type))

        raise DSLParsingLogicException(
                50, "Input type validation failed: Input '{0}' type "
                    "is '{1}', yet it was assigned with the value '{2}'"
                    .format(input_key, input_type, input_val))


def merge_schema_and_instance_inputs(schema_inputs,
                                     instance_inputs):

    flattened_schema_inputs = utils.flatten_schema(schema_inputs)
    merged_inputs = dict(
            flattened_schema_inputs.items() +
            instance_inputs.items())

    validate_missing_inputs(merged_inputs, schema_inputs)
    validate_inputs_types(merged_inputs, schema_inputs)
    return merged_inputs


def operation_mapping(implementation, inputs, executor,
                      max_retries, retry_interval):
    return {
        'implementation': implementation,
        'inputs': inputs,
        'executor': executor,
        'max_retries': max_retries,
        'retry_interval': retry_interval
    }


def no_op():
    return operation_mapping(
            implementation='',
            inputs={},
            executor=None,
            max_retries=None,
            retry_interval=None,
    )


def no_op_operation(operation_name):
    return operation(
            name=operation_name,
            plugin_name='',
            operation_mapping='',
            operation_inputs={},
            executor=None,
            max_retries=None,
            retry_interval=None
    )


def operation(name,
              plugin_name,
              operation_mapping,
              operation_inputs,
              executor,
              max_retries,
              retry_interval):
    return {
        'name': name,
        'plugin': plugin_name,
        'operation': operation_mapping,
        'executor': executor,
        'inputs': operation_inputs,
        'has_intrinsic_functions': False,
        'max_retries': max_retries,
        'retry_interval': retry_interval
    }


def workflow_operation(plugin_name,
                       workflow_mapping,
                       workflow_parameters):
    return {
        'plugin': plugin_name,
        'operation': workflow_mapping,
        'parameters': workflow_parameters
    }
