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

from dsl_parser import (constants,
                        models)
from dsl_parser.elements import (imports,
                                 misc,
                                 plugins,
                                 node_types,
                                 node_templates,
                                 relationships,
                                 workflows,
                                 policies,
                                 data_types,
                                 version as _version)
from dsl_parser.framework.elements import Element
from dsl_parser.framework.requirements import Value


class BlueprintVersionExtractor(Element):

    schema = {
        'tosca_definitions_version': _version.ToscaDefinitionsVersion,
        # here so it gets version validated
        'dsl_definitions': misc.DSLDefinitions,
    }
    requires = {
        _version.ToscaDefinitionsVersion: ['version',
                                           Value('plan_version')]
    }

    def parse(self, version, plan_version):
        return {
            'version': version,
            'plan_version': plan_version
        }


class BlueprintImporter(Element):

    schema = {
        'imports': imports.ImportsLoader,
    }
    requires = {
        imports.ImportsLoader: ['resource_base']
    }

    def parse(self, resource_base):
        return {
            'merged_blueprint': self.child(imports.ImportsLoader).value,
            'resource_base': resource_base
        }


class Blueprint(Element):

    schema = {
        'tosca_definitions_version': _version.ToscaDefinitionsVersion,
        'description': misc.Description,
        'imports': imports.Imports,
        'dsl_definitions': misc.DSLDefinitions,
        'inputs': misc.Inputs,
        'plugins': plugins.Plugins,
        'node_types': node_types.NodeTypes,
        'relationships': relationships.Relationships,
        'node_templates': node_templates.NodeTemplates,
        'policy_types': policies.PolicyTypes,
        'policy_triggers': policies.PolicyTriggers,
        'groups': policies.Groups,
        'policies': policies.Policies,
        'workflows': workflows.Workflows,
        'outputs': misc.Outputs,
        'data_types': data_types.DataTypes
    }

    requires = {
        node_templates.NodeTemplates: ['deployment_plugins_to_install'],
        workflows.Workflows: ['workflow_plugins_to_install'],
        policies.Policies: ['scaling_groups']
    }

    def parse(self, workflow_plugins_to_install,
              deployment_plugins_to_install,
              scaling_groups):
        return models.Plan({
            constants.DESCRIPTION: self.child(misc.Description).value,
            constants.NODES: self.child(node_templates.NodeTemplates).value,
            constants.RELATIONSHIPS: self.child(
                relationships.Relationships).value,
            constants.WORKFLOWS: self.child(workflows.Workflows).value,
            constants.POLICY_TYPES: self.child(policies.PolicyTypes).value,
            constants.POLICY_TRIGGERS:
                self.child(policies.PolicyTriggers).value,
            constants.POLICIES:
                self.child(policies.Policies).value,
            constants.GROUPS: self.child(policies.Groups).value,
            constants.SCALING_GROUPS: scaling_groups or {},
            constants.INPUTS: self.child(misc.Inputs).value,
            constants.OUTPUTS: self.child(misc.Outputs).value,
            constants.DEPLOYMENT_PLUGINS_TO_INSTALL:
                deployment_plugins_to_install,
            constants.WORKFLOW_PLUGINS_TO_INSTALL: workflow_plugins_to_install,
            constants.VERSION: self.child(
                _version.ToscaDefinitionsVersion).value
        })
