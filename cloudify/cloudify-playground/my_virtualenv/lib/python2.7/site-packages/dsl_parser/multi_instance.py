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


import copy

from dsl_parser import (models,
                        rel_graph,
                        constants)


def create_deployment_plan(plan):
    """
    Expand node instances based on number of instances to deploy and
    defined relationships
    """
    deployment_plan = copy.deepcopy(plan)
    plan_node_graph = rel_graph.build_node_graph(
        nodes=deployment_plan['nodes'],
        scaling_groups=deployment_plan['scaling_groups'])
    deployment_node_graph, ctx = rel_graph.build_deployment_node_graph(
        plan_node_graph)
    node_instances = rel_graph.extract_node_instances(
        node_instances_graph=deployment_node_graph,
        ctx=ctx)
    deployment_plan[constants.NODE_INSTANCES] = node_instances
    return models.Plan(deployment_plan)


def modify_deployment(nodes,
                      previous_nodes,
                      previous_node_instances,
                      modified_nodes,
                      scaling_groups):
    """
    modifies deployment according to the expected nodes. based on
    previous_node_instances
    :param nodes: the entire set of expected nodes.
    :param previous_node_instances:
    :param modified_nodes: existing nodes whose instance number has changed
     Add a line note
    :return: a dict of add,extended,reduced and removed instances
     Add a line note
    """

    plan_node_graph = rel_graph.build_node_graph(
        nodes=nodes,
        scaling_groups=scaling_groups)
    previous_plan_node_graph = rel_graph.build_node_graph(
        nodes=previous_nodes,
        scaling_groups=scaling_groups)
    previous_deployment_node_graph, previous_deployment_contained_graph = \
        rel_graph.build_previous_deployment_node_graph(
            plan_node_graph=previous_plan_node_graph,
            previous_node_instances=previous_node_instances)
    new_deployment_node_graph, ctx = rel_graph.build_deployment_node_graph(
        plan_node_graph=plan_node_graph,
        previous_deployment_node_graph=previous_deployment_node_graph,
        previous_deployment_contained_graph=previous_deployment_contained_graph,  # noqa
        modified_nodes=modified_nodes)

    # Any node instances which were added or removed
    added_and_related = rel_graph.extract_added_node_instances(
        previous_deployment_node_graph, new_deployment_node_graph,
        ctx=ctx)
    removed_and_related = rel_graph.extract_removed_node_instances(
        previous_deployment_node_graph, new_deployment_node_graph,
        ctx=ctx)

    # Any node instances which had a modification to their relationship.
    # (newly introduced and removed nodes)
    extended_and_related = rel_graph.extract_added_relationships(
        previous_deployment_node_graph, new_deployment_node_graph,
        ctx=ctx)
    reduced_and_related = rel_graph.extract_removed_relationships(
        previous_deployment_node_graph, new_deployment_node_graph,
        ctx=ctx)

    # The extracted extended and reduced relationships hold the new and old
    # node instances. These are not required, since the change is on
    # node instance level (and not the relationship level)
    extended_and_related = \
        filter_out_node_instances(added_and_related, extended_and_related)
    reduced_and_related = \
        filter_out_node_instances(removed_and_related, reduced_and_related)

    return {
        'added_and_related': added_and_related,
        'extended_and_related': extended_and_related,
        'reduced_and_related': reduced_and_related,
        'removed_and_related': removed_and_related
    }


def filter_out_node_instances(node_instances_to_filter_out,
                              base_node_instances):
    instance_ids_to_remove = [n['id'] for n in node_instances_to_filter_out
                              if 'modification' in n]
    return [n for n in base_node_instances
            if n['id'] not in instance_ids_to_remove]
