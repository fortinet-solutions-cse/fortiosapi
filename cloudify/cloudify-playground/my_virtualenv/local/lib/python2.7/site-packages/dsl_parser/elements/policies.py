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

import itertools

import networkx as nx

from dsl_parser import (exceptions,
                        utils,
                        constants)
from dsl_parser.elements import (node_templates as _node_templates,
                                 data_types,
                                 scalable,
                                 version as _version)
from dsl_parser.framework.requirements import Value
from dsl_parser.framework.elements import (DictElement,
                                           Element,
                                           Leaf,
                                           List,
                                           Dict)


class PolicyTriggerSource(Element):

    required = True
    schema = Leaf(type=basestring)


class PolicyTrigger(DictElement):

    schema = {
        'parameters': data_types.Schema,
        'source': PolicyTriggerSource,
    }


class PolicyTypeSource(Element):

    required = True
    schema = Leaf(type=basestring)


class PolicyType(DictElement):

    schema = {
        'properties': data_types.Schema,
        'source': PolicyTypeSource,
    }


class PolicyTypes(DictElement):

    schema = Dict(type=PolicyType)


class PolicyTriggers(DictElement):

    schema = Dict(type=PolicyTrigger)


class GroupPolicyType(Element):

    required = True
    schema = Leaf(type=basestring)
    requires = {
        PolicyTypes: [Value('policy_types')]
    }

    def validate(self, policy_types):
        if self.initial_value not in policy_types:
            raise exceptions.DSLParsingLogicException(
                41,
                "Policy '{0}' of group '{1}' references a non existent "
                "policy type '{2}'"
                .format(self.ancestor(GroupPolicy).name,
                        self.ancestor(Group).name,
                        self.initial_value))


class GroupPolicyProperties(Element):

    schema = Leaf(type=dict)
    requires = {
        GroupPolicyType: [],
        PolicyTypes: [Value('policy_types')],
        data_types.DataTypes: [Value('data_types')]
    }

    def parse(self, policy_types, data_types):
        policy_type = policy_types[self.sibling(GroupPolicyType).value]
        policy_type_properties = policy_type.get('properties', {})
        return utils.merge_schema_and_instance_properties(
            self.initial_value or {},
            policy_type_properties,
            data_types,
            "{0} '{1}' property is not part of "
            "the policy type properties schema",
            "{0} does not provide a value for mandatory "
            "'{1}' property which is "
            "part of its policy type schema",
            node_name="group '{0}', policy '{1}'".format(
                self.ancestor(Group).name,
                self.ancestor(GroupPolicy).name))


class GroupPolicyTriggerType(Element):

    required = True
    schema = Leaf(type=basestring)
    requires = {
        PolicyTriggers: [Value('policy_triggers')]
    }

    def validate(self, policy_triggers):
        if self.initial_value not in policy_triggers:
            raise exceptions.DSLParsingLogicException(
                42,
                "Trigger '{0}' of policy '{1}' of group '{2}' "
                "references a non existent "
                "'policy trigger '{3}'"
                .format(self.ancestor(GroupPolicyTrigger).name,
                        self.ancestor(GroupPolicy).name,
                        self.ancestor(Group).name,
                        self.initial_value))


class GroupPolicyTriggerParameters(Element):

    schema = Leaf(type=dict)
    requires = {
        GroupPolicyTriggerType: [],
        PolicyTriggers: [Value('policy_triggers')],
        data_types.DataTypes: [Value('data_types')]
    }

    def parse(self, policy_triggers, data_types):
        trigger_type = policy_triggers[
            self.sibling(GroupPolicyTriggerType).value]
        policy_trigger_parameters = trigger_type.get('parameters', {})
        return utils.merge_schema_and_instance_properties(
            self.initial_value or {},
            policy_trigger_parameters,
            data_types,
            "{0} '{1}' property is not part of "
            "the policy type properties schema",
            "{0} does not provide a value for mandatory "
            "'{1}' property which is "
            "part of its policy type schema",
            node_name="group '{0}', policy '{1}' trigger '{2}'"
                      .format(self.ancestor(Group).name,
                              self.ancestor(GroupPolicy).name,
                              self.ancestor(GroupPolicyTrigger).name))


class GroupPolicyTrigger(DictElement):

    schema = {
        'type': GroupPolicyTriggerType,
        'parameters': GroupPolicyTriggerParameters,
    }


class GroupPolicyTriggers(DictElement):

    schema = Dict(type=GroupPolicyTrigger)


class GroupPolicy(DictElement):

    schema = {
        'type': GroupPolicyType,
        'properties': GroupPolicyProperties,
        'triggers': GroupPolicyTriggers,
    }


class GroupMember(Element):

    schema = Leaf(type=basestring)
    requires = {
        _node_templates.NodeTemplates: ['node_template_names']
    }

    def validate(self, node_template_names):
        groups = self.ancestor(Groups).initial_value
        value = self.initial_value
        group_names = set(groups.keys()) if groups else set()
        if value not in node_template_names and value not in group_names:
            raise exceptions.DSLParsingLogicException(
                40,
                "Member '{0}' of group '{1}' does not "
                "match any defined node".format(
                    value,
                    self.ancestor(Group).name))


class GroupMembers(Element):

    required = True
    schema = List(type=GroupMember)

    def validate(self):
        if len(self.children()) < 1:
            raise exceptions.DSLParsingFormatException(
                1, "At least one member should be specified")

    def parse(self):
        # ensure uniqueness
        return list(set([c.value for c in self.children()]))


class GroupPolicies(DictElement):

    schema = Dict(type=GroupPolicy)


class Group(DictElement):

    schema = {
        'members': GroupMembers,
        'policies': GroupPolicies,
    }
    requires = {
        _node_templates.NodeTemplates: ['node_template_names']
    }

    def validate(self, node_template_names):
        if self.name in node_template_names:
            raise exceptions.DSLParsingLogicException(
                exceptions.ERROR_GROUP_AND_NODE_TEMPLATE_SAME_NAME,
                "Both a group and a node template are named '{0}'"
                .format(self.name))


class Groups(DictElement):

    schema = Dict(type=Group)


class PolicyInstanceType(Element):

    required = True
    schema = Leaf(type=basestring)

    def validate(self):
        scaling_policy = constants.SCALING_POLICY
        if self.initial_value != scaling_policy:
            raise exceptions.DSLParsingLogicException(
                exceptions.ERROR_UNSUPPORTED_POLICY,
                "'{0}' policy type is not implemented. "
                "Only '{1}' policy type is supported."
                .format(self.initial_value, scaling_policy))


class PolicyInstanceTarget(Element):

    schema = Leaf(type=basestring)
    requires = {
        Groups: [Value('groups')]
    }

    def validate(self, groups):
        if self.initial_value not in groups:
            raise exceptions.DSLParsingLogicException(
                exceptions.ERROR_NON_GROUP_TARGET,
                "'{0}' is not a valid policy target. Only groups are "
                "valid policy targets. Defined groups are {1}."
                .format(self.initial_value, groups))


class PolicyInstanceTargets(Element):

    required = True
    schema = List(type=PolicyInstanceTarget)

    def validate(self):
        if len(self.children()) < 1:
            raise exceptions.DSLParsingLogicException(
                exceptions.ERROR_NO_TARGETS,
                "Policy '{0}' has no targets groups defined for it. "
                "At least one target group is required."
                .format(self.ancestor(Policy).name))


class Policy(DictElement):

    schema = {
        'type': PolicyInstanceType,
        # TODO: policies should be implemented according to TOSCA
        # as generic types
        'properties': scalable.Properties,
        'targets': PolicyInstanceTargets
    }

    def parse(self, **kwargs):
        result = self.build_dict_result()
        if 'properties' not in result:
            result['properties'] = scalable.Properties.DEFAULT.copy()
        return result


class Policies(DictElement):

    schema = Dict(type=Policy)
    requires = {
        Groups: [Value('groups')],
        _node_templates.NodeTemplates: [Value('node_templates')],
        _version.ToscaDefinitionsVersion: ['version'],
        'inputs': ['validate_version']
    }
    provides = ['scaling_groups']

    def validate(self, version, validate_version, **kwargs):
        if validate_version:
            self.validate_version(version, (1, 3))

    def calculate_provided(self, groups, node_templates, **kwargs):
        scaling_groups = self._create_scaling_groups(groups)
        # we can't perform the validation in "validate" because we need
        # the parsed value of "policies" which is only calculated in "parse"
        self._validate_and_update_groups(scaling_groups, node_templates)
        return {
            'scaling_groups': scaling_groups
        }

    def _create_scaling_groups(self, groups):
        policies = self.value
        scaling_policies = [policy for policy in policies.values()
                            if policy['type'] == constants.SCALING_POLICY]
        scaling_groups = {}
        for policy in scaling_policies:
            properties = policy['properties']
            for target in policy['targets']:
                group = groups[target]
                scaling_groups[target] = {
                    'members': group['members'],
                    'properties': properties
                }
        return scaling_groups

    def _validate_and_update_groups(self, scaling_groups, node_templates):

        member_graph = nx.DiGraph()
        for group_name, group in scaling_groups.items():
            for member in group['members']:
                member_graph.add_edge(member, group_name)

        node_graph = nx.DiGraph()
        for node in node_templates:
            node_graph.add_node(node['id'])
            for rel in node.get(constants.RELATIONSHIPS, []):
                if constants.CONTAINED_IN_REL_TYPE in rel['type_hierarchy']:
                    node_graph.add_edge(node['id'], rel['target_id'])

        self._validate_no_group_cycles(member_graph)
        self._validate_members_in_one_group_only(member_graph)
        self._validate_no_contained_in_shares_group_with_non_contained_in(
            member_graph, node_graph)
        self._remove_contained_nodes_from_scaling_groups(
            scaling_groups, member_graph, node_graph)

    @staticmethod
    def _validate_no_group_cycles(member_graph):
        # verify no group cycles (i.e. group A in group B and vice versa)
        group_cycles = nx.recursive_simple_cycles(member_graph)
        if group_cycles:
            raise exceptions.DSLParsingLogicException(
                exceptions.ERROR_GROUP_CYCLE,
                'Illegal group cycles found: {0}'.format(group_cycles))

    @staticmethod
    def _validate_members_in_one_group_only(member_graph):
        # verify all group members are part of exactly one group
        for member in member_graph:
            successors = member_graph.successors(member)
            if len(successors) > 1:
                raise exceptions.DSLParsingLogicException(
                    exceptions.ERROR_MULTIPLE_GROUPS,
                    "Nodes and groups cannot be members in multiple groups, "
                    "but member '{0}' belongs to the following multiple "
                    "groups: {1}".format(member, successors))

    @staticmethod
    def _validate_no_contained_in_shares_group_with_non_contained_in(
            member_graph, node_graph):
        # for each node a, if node a is (recursively) contained in node b
        # verify that it is not contained in (recursively) a group that has
        # nodes that are not (recursively) contained in node b too unless
        # node b is in that group as well

        # first extract all group members (recursively)
        group_members = {}
        for member in member_graph:
            if member in node_graph:
                continue
            group_members[member] = nx.ancestors(member_graph, member)

        # next, remove members that are groups themselves
        group_names = set(group_members.keys())
        group_node_members = {}
        for group_name, members in group_members.items():
            group_node_members[group_name] = members - group_names

        # now, for each group, for each node pair, verify both nodes in pair
        # are contained (recursively) in some third node or one of them is
        # contained in some third node that has this property
        containing_nodes = {}

        def check_pair(pair_key):
            node_a, node_b = pair_key
            if node_a == node_b:
                return True
            if node_a not in containing_nodes:
                containing_nodes[node_a] = nx.topological_sort(
                    node_graph, nbunch=[node_a])
            if node_b not in containing_nodes:
                containing_nodes[node_b] = nx.topological_sort(
                    node_graph, nbunch=[node_b])
            a_containing_nodes = set(containing_nodes[node_a])
            a_containing_nodes.remove(node_a)
            b_containing_nodes = set(containing_nodes[node_b])
            b_containing_nodes.remove(node_b)
            if not (a_containing_nodes or b_containing_nodes):
                return True
            if node_b in a_containing_nodes:
                return True
            if node_a in b_containing_nodes:
                return True
            if a_containing_nodes & b_containing_nodes:
                return True
            return False

        checked_pairs = set()
        ok_pairs = set()
        problematic_pairs = set()
        for node_members in group_node_members.values():
            for node_a, node_b in itertools.product(node_members, repeat=2):
                pair_key = tuple(sorted([node_a, node_b]))
                if pair_key in checked_pairs:
                    continue
                if check_pair(pair_key):
                    ok_pairs.add(pair_key)
                else:
                    problematic_pairs.add(pair_key)
                checked_pairs.add(pair_key)

        def check_problematic_pair(node_a, node_b):
            for node_a_containing_node in containing_nodes[node_a]:
                pair_key = tuple(sorted([node_b, node_a_containing_node]))
                if pair_key in ok_pairs:
                    return True
            for node_b_containing_node in containing_nodes[node_b]:
                pair_key = tuple(sorted([node_a, node_b_containing_node]))
                if pair_key in ok_pairs:
                    return True
            return False

        for node_a, node_b in problematic_pairs:
            if check_problematic_pair(node_a, node_b):
                ok_pairs.add((node_a, node_b))
            else:
                raise exceptions.DSLParsingLogicException(
                    exceptions.ERROR_NON_CONTAINED_GROUP_MEMBERS,
                    "Node '{0}' and '{1}' belong to some shared group but "
                    "they are not contained in any shared node, nor is any "
                    "ancestor node of theirs.".format(node_a, node_b))

    @staticmethod
    def _remove_contained_nodes_from_scaling_groups(
            scaling_groups, member_graph, node_graph):
        # for each node, if a node is (recursively) with
        # a node that contains it (recursively), remove the offending
        # member from the relevant group.
        # if the node and its containee are in the same group, remove the
        # containee, otherwise, remove the group closest to the containing
        # node
        for member in member_graph:
            if member not in node_graph:
                continue
            containing_groups = nx.topological_sort(member_graph,
                                                    nbunch=[member])
            containing_nodes = nx.topological_sort(node_graph, nbunch=[member])
            for node in containing_nodes:
                if node == member:
                    continue
                if node not in member_graph:
                    continue

                containing_node_groups = nx.topological_sort(member_graph,
                                                             nbunch=[node])
                containing_node_groups_set = set(containing_node_groups)

                shared_groups = (set(containing_groups) &
                                 containing_node_groups_set)
                if not shared_groups:
                    continue

                minimal_containing_group = nx.topological_sort(
                    member_graph, nbunch=shared_groups)[0]
                direct_member_group = member_graph.successors(member)[0]
                members = scaling_groups[minimal_containing_group]['members']
                if direct_member_group == minimal_containing_group:
                    removed_member = member
                else:
                    for containing_group in reversed(containing_groups):
                        if containing_group not in containing_node_groups_set:
                            removed_member = containing_group
                            break
                    else:
                        raise RuntimeError('Illegal state')

                if removed_member in members:
                    members.remove(removed_member)
