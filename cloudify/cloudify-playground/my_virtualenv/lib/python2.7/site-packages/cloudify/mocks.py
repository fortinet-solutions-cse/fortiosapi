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


from cloudify.context import (CloudifyContext,
                              ContextCapabilities,
                              BootstrapContext)
from cloudify.utils import setup_logger


class MockRelationshipSubjectContext(object):
    def __init__(self, node, instance):
        self.node = node
        self.instance = instance


class MockRelationshipContext(object):
    def __init__(self, target, type=None):
        self.target = target
        self.type = type


class MockNodeInstanceContext(object):

    def __init__(self, id=None, runtime_properties=None, relationships=None):
        self._id = id
        self._runtime_properties = runtime_properties
        if relationships is None:
            relationships = []
        self._relationships = relationships

    @property
    def id(self):
        return self._id

    @property
    def runtime_properties(self):
        return self._runtime_properties

    @property
    def relationships(self):
        return self._relationships

    def update(self):
        pass


class MockNodeContext(object):

    def __init__(self, id=None, properties=None):
        self._id = id
        self._properties = properties

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._id

    @property
    def properties(self):
        return self._properties


class MockContext(dict):

    def __init__(self, values=None):
        self.update(values or {})

    def __getattr__(self, item):
        return self[item]


class MockCloudifyContext(CloudifyContext):
    """
    Cloudify context mock that can be used when testing Cloudify plugins.
    """

    def __init__(self,
                 node_id=None,
                 node_name=None,
                 blueprint_id=None,
                 deployment_id=None,
                 execution_id=None,
                 properties=None,
                 runtime_properties=None,
                 relationships=None,
                 capabilities=None,
                 related=None,
                 source=None,
                 target=None,
                 operation=None,
                 resources=None,
                 provider_context=None,
                 bootstrap_context=None):
        super(MockCloudifyContext, self).__init__({
            'blueprint_id': blueprint_id,
            'deployment_id': deployment_id,
            'node_id': node_id,
            'node_name': node_name,
            'node_properties': properties,
            'operation': operation})
        self._node_id = node_id
        self._node_name = node_name
        self._deployment_id = deployment_id
        self._execution_id = execution_id
        self._properties = properties or {}
        self._runtime_properties = runtime_properties or {}
        self._resources = resources or {}
        self._source = source
        self._target = target
        if capabilities and not isinstance(capabilities, ContextCapabilities):
            raise ValueError(
                "MockCloudifyContext(capabilities=?) must be "
                "instance of ContextCapabilities, not {0}".format(
                    capabilities))
        self._related = related
        self._provider_context = provider_context or {}
        self._bootstrap_context = bootstrap_context or BootstrapContext({})
        self._mock_context_logger = setup_logger('mock-context-logger')
        if node_id:
            self._instance = MockNodeInstanceContext(
                id=node_id,
                runtime_properties=self._runtime_properties,
                relationships=relationships)
            self._capabilities = capabilities or ContextCapabilities(
                self._endpoint, self._instance)
            self._node = MockNodeContext(node_name, properties)
        if self._source is None and self._target:
            self._source = MockContext({
                'instance': None,
                'node': None
            })

    @property
    def execution_id(self):
        return self._execution_id

    @property
    def capabilities(self):
        return self._capabilities

    @property
    def logger(self):
        return self._mock_context_logger

    @property
    def provider_context(self):
        return self._provider_context

    @property
    def bootstrap_context(self):
        return self._bootstrap_context

    def download_resource(self, resource_path, target_path=None):
        if target_path:
            raise RuntimeError("MockCloudifyContext does not support "
                               "download_resource() with target_path yet")
        if resource_path not in self._resources:
            raise RuntimeError(
                "Resource '{0}' was not found. "
                "Available resources: {1}".format(resource_path,
                                                  self._resources.keys()))
        return self._resources[resource_path]

    def get_resource(self, resource_path):
        raise RuntimeError('get_resource() not implemented in context mock')

    def __contains__(self, key):
        return key in self._properties or key in self._runtime_properties

    def __setitem__(self, key, value):
        self._runtime_properties[key] = value

    def __getitem__(self, key):
        if key in self._properties:
            return self._properties[key]
        return self._runtime_properties[key]
