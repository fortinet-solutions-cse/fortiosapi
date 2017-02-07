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


class Version(dict):

    def __init__(self, version):
        self.update(version)

    @property
    def raw(self):
        return self['raw']

    @property
    def definitions_name(self):
        return self['definitions_name']

    @property
    def definitions_version(self):
        return self['definitions_version']


class Plan(dict):

    def __init__(self, plan):
        self.update(plan)

    @property
    def version(self):
        return self['version']

    @property
    def inputs(self):
        return self['inputs']

    @property
    def outputs(self):
        return self['outputs']

    @property
    def node_templates(self):
        return self['nodes']
