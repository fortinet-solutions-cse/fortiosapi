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


def operation(func=None, **kwargs):
    """This decorator does not do anything and is kept for backwards
       compatibility. It is not required for operations to work.
    """
    return func or operation


def workflow(func=None, system_wide=False, **kwargs):
    """This decorator should only be used to decorate system wide
       workflows. It is not required for regular workflows.
    """
    if func:
        func.workflow_system_wide = system_wide
        return func
    else:
        return lambda fn: workflow(fn, system_wide)


task = operation
