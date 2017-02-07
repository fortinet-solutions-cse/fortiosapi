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


class MissingRequiredInputError(Exception):
    """
    An error raised when a deployment is created and a required input
    was not specified on its creation.
    """
    def __init__(self, *args, **kwargs):
        super(MissingRequiredInputError, self).__init__(*args, **kwargs)


class UnknownInputError(Exception):
    """
    An error raised when an unknown input is specified on deployment creation.
    """
    def __init__(self, *args, **kwargs):
        super(UnknownInputError, self).__init__(*args, **kwargs)


class FunctionEvaluationError(Exception):
    """
    An error raised when an intrinsic function was unable to get evaluated.
    """
    def __init__(self, func_name, message=None):
        msg = 'Unable to evaluate {0} function'.format(func_name)
        if message:
            msg = '{0}: {1}'.format(msg, message)
        super(FunctionEvaluationError, self).__init__(msg)


class DSLParsingException(Exception):
    def __init__(self, err_code, *args):
        super(DSLParsingException, self).__init__(*args)
        self.err_code = err_code
        self.element = None

    def __str__(self):
        message = super(DSLParsingException, self).__str__()
        if not self.element:
            return message
        return '{0} {1}'.format(message, self.element)


class DSLParsingLogicException(DSLParsingException):
    pass


class DSLParsingFormatException(DSLParsingException):
    pass


class DSLParsingElementMatchException(DSLParsingException):
    """
    An error raised when element child/ancestor lookup fails (element not
    found)
    """
    pass


class DSLParsingSchemaAPIException(DSLParsingException):
    """
    An error raised due to invalid usage of framework
    """
    pass


class IllegalConnectedToConnectionType(Exception):
    pass


class UnsupportedRelationship(Exception):
    pass


class IllegalAllToOneState(Exception):
    pass


class UnsupportedAllToOneInGroup(Exception):
    pass


ERROR_CODE_CYCLE = 100
ERROR_CODE_ILLEGAL_VALUE_ACCESS = 101
ERROR_CODE_DSL_DEFINITIONS_VERSION_MISMATCH = 102
ERROR_UNKNOWN_TYPE = 103
ERROR_INVALID_TYPE_NAME = 104
ERROR_VALUE_DOES_NOT_MATCH_TYPE = 105
ERROR_GROUP_CYCLE = 200
ERROR_MULTIPLE_GROUPS = 201
ERROR_NON_CONTAINED_GROUP_MEMBERS = 202
ERROR_UNSUPPORTED_POLICY = 204
ERROR_NON_GROUP_TARGET = 205
ERROR_NO_TARGETS = 206
ERROR_INVALID_INSTANCES = 207
ERROR_INVALID_LITERAL_INSTANCES = 208
ERROR_INSTANCES_DEPLOY_AND_CAPABILITIES = 209
ERROR_INVALID_DICT_VALUE = 210
ERROR_GROUP_AND_NODE_TEMPLATE_SAME_NAME = 211
