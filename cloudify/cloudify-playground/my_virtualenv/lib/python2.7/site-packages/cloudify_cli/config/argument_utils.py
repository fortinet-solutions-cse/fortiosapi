########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


import copy


def remove_completer(argument):
    argument_copy = copy.copy(argument)
    del argument_copy['completer']
    return argument_copy


def make_optional(argument):
    argument_copy = copy.copy(argument)
    argument_copy['required'] = False
    return argument_copy


def make_required(argument):
    argument_copy = copy.copy(argument)
    argument_copy['required'] = True
    return argument_copy


def remove_type(argument):
    argument_copy = copy.copy(argument)
    del argument_copy['type']
    return argument_copy
