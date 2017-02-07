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
import collections
import random

import networkx as nx

from dsl_parser import constants
from dsl_parser import exceptions

NODES = 'nodes'
RELATIONSHIPS = 'relationships'
DEPENDS_ON_REL_TYPE = constants.DEPENDS_ON_REL_TYPE
CONNECTED_TO_REL_TYPE = constants.CONNECTED_TO_REL_TYPE
CONTAINED_IN_REL_TYPE = constants.CONTAINED_IN_REL_TYPE
GROUP_CONTAINED_IN_REL_TYPE = '__group_contained_in__'
CONNECTION_TYPE = 'connection_type'
ALL_TO_ALL = 'all_to_all'
ALL_TO_ONE = 'all_to_one'


def build_node_graph(nodes, scaling_groups):

    graph = nx.DiGraph()
    groups_graph = nx.DiGraph()
    node_ids = set()
    contained_in_group = {}

    for node in nodes:
        node_id = node['id']
        node_ids.add(node_id)
        if 'capabilities' in node:
            # This code path is used by unit tests
            scale_properties = node['capabilities']['scalable']['properties']
        else:
            # This code path is used by actual code
            scale_properties = {
                'current_instances': node['number_of_instances'],
                'default_instances':
                    node['deploy_number_of_instances'],
                'min_instances': node['min_number_of_instances'],
                'max_instances': node['max_number_of_instances']
            }
        graph.add_node(node_id,
                       node=node,
                       scale_properties=scale_properties)

    for group_name, group in scaling_groups.items():
        scale_properties = group['properties']
        groups_graph.add_node(group_name)
        graph.add_node(group_name,
                       node={'id': group_name, 'group': True},
                       scale_properties=scale_properties)

    for group_name, group in scaling_groups.items():
        for member in group['members']:
            graph.add_edge(member, group_name,
                           relationship={
                               'type': GROUP_CONTAINED_IN_REL_TYPE,
                               'type_hierarchy': [GROUP_CONTAINED_IN_REL_TYPE],
                               'target_id': group_name
                           },
                           index=-1)
            groups_graph.add_edge(member, group_name)
            if member in node_ids:
                contained_in_group[member] = group_name

    for node in nodes:
        node_id = node['id']
        for index, relationship in enumerate(node.get(RELATIONSHIPS, [])):
            target_id = relationship['target_id']
            if (CONTAINED_IN_REL_TYPE in relationship['type_hierarchy'] and
                    node_id in contained_in_group):
                group_name = contained_in_group[node_id]
                relationship['target_id'] = group_name
                relationship['replaced'] = target_id
                graph.add_edge(node_id, group_name,
                               relationship=relationship,
                               index=index)
                top_level_group_name = nx.topological_sort(
                    groups_graph, nbunch=[group_name])[-1]
                graph.add_edge(
                    top_level_group_name, target_id,
                    relationship={
                        'type': GROUP_CONTAINED_IN_REL_TYPE,
                        'type_hierarchy': [GROUP_CONTAINED_IN_REL_TYPE],
                        'target_id': target_id
                    },
                    index=-1)
            else:
                graph.add_edge(node_id, target_id,
                               relationship=relationship,
                               index=index)

    return graph


def build_previous_deployment_node_graph(plan_node_graph,
                                         previous_node_instances):
    graph = nx.DiGraph()
    contained_graph = nx.DiGraph()
    for node_instance in previous_node_instances:
        node_instance_id = node_instance['id']
        node_instance_host_id = node_instance.get('host_id')
        graph.add_node(node_instance_id,
                       node=node_instance)
        contained_graph.add_node(node_instance_id,
                                 node=node_instance)
        scaling_groups = node_instance.get('scaling_groups') or ()
        for scaling_group in scaling_groups:
            group_id = scaling_group['id']
            group_name = scaling_group['name']
            node = {'id': group_id, 'name': group_name, 'group': True}
            if node_instance_host_id:
                node['host_id'] = node_instance_host_id
            graph.add_node(group_id, node=node)
            contained_graph.add_node(group_id, node=node)

    for node_instance in previous_node_instances:
        node_instance_id = node_instance['id']
        node_id = _node_id_from_node_instance(node_instance)
        scaling_groups = node_instance.get('scaling_groups')
        contained_in_target_id = None
        contained_in_target_name = None
        for index, rel in enumerate(node_instance.get('relationships', [])):
            target_id = rel['target_id']
            target_name = rel['target_name']
            # if the original relationship does not exist in the plan node
            # graph, it means it was a contained_in relationship that was
            # replaced by a scaling group
            replaced_contained_in = target_name not in plan_node_graph[node_id]
            if replaced_contained_in:
                contained_in_target_id = target_id
                contained_in_target_name = target_name
                # for the purpose of containment, only the first group
                # is relevant
                scaling_group = scaling_groups[0]
                rel['target_id'] = scaling_group['id']
                rel['target_name'] = scaling_group['name']
                rel['replaced'] = True
                graph.add_edge(node_instance_id, scaling_group['id'],
                               relationship=rel,
                               index=index)
                contained_graph.add_edge(node_instance_id, scaling_group['id'])
            else:
                graph.add_edge(node_instance_id, target_id,
                               relationship=rel,
                               index=index)
                if _relationship_type_hierarchy_includes_one_of(
                    plan_node_graph[node_id][target_name]['relationship'],
                        [CONTAINED_IN_REL_TYPE]):
                    contained_graph.add_edge(node_instance_id, target_id)

        if scaling_groups:
            scaling_groups = scaling_groups[:]
            if contained_in_target_id:
                scaling_groups.append({
                    'id': contained_in_target_id,
                    'name': contained_in_target_name
                })
            else:
                scaling_groups.insert(0, {
                    'id': node_instance_id,
                    'name': node_id
                })
            for i in range(len(scaling_groups) - 1):
                graph.add_edge(
                    scaling_groups[i]['id'],
                    scaling_groups[i+1]['id'],
                    relationship={
                        'type': GROUP_CONTAINED_IN_REL_TYPE,
                        'target_id': scaling_groups[i+1]['id'],
                        'target_name': scaling_groups[i+1]['name']
                    },
                    index=-1)
                contained_graph.add_edge(scaling_groups[i]['id'],
                                         scaling_groups[i+1]['id'])
    return graph, contained_graph


def build_deployment_node_graph(plan_node_graph,
                                previous_deployment_node_graph=None,
                                previous_deployment_contained_graph=None,
                                modified_nodes=None):

    _verify_no_unsupported_relationships(plan_node_graph)

    deployment_node_graph = nx.DiGraph()
    ctx = Context(
        plan_node_graph=plan_node_graph,
        deployment_node_graph=deployment_node_graph,
        previous_deployment_node_graph=previous_deployment_node_graph,
        previous_deployment_contained_graph=previous_deployment_contained_graph,  # noqa
        modified_nodes=modified_nodes)

    _handle_contained_in(ctx)

    ctx.node_instance_ids.clear()
    ctx.node_ids_to_node_instance_ids.clear()
    for node_instance_id, data in deployment_node_graph.nodes_iter(
            data=True):
        ctx.node_instance_ids.add(node_instance_id)
        node_id = _node_id_from_node_instance(data['node'])
        ctx.node_ids_to_node_instance_ids[node_id].add(node_instance_id)

    _handle_connected_to_and_depends_on(ctx)

    ctx.restore_plan_node_graph()

    return deployment_node_graph, ctx


def extract_node_instances(node_instances_graph,
                           ctx,
                           copy_instances=False,
                           contained_graph=None):
    contained_graph = contained_graph or ctx.deployment_contained_graph
    node_instances = []
    for node_instance_id, data in node_instances_graph.nodes_iter(data=True):
        node_instance = data['node']
        if node_instance.get('group'):
            continue
        node_instance_attributes = data.get('node_instance_attributes')
        if copy_instances:
            node_instance = copy.deepcopy(node_instance)
        if node_instance_attributes:
            node_instance.update(node_instance_attributes)
        indexed_relationship_instances = []
        for target_node_instance_id in node_instances_graph.neighbors_iter(
                node_instance_id):
            edge_data = node_instances_graph[node_instance_id][
                target_node_instance_id]
            relationship_instance = edge_data['relationship']
            relationship_index = edge_data['index']
            if copy_instances:
                relationship_instance = copy.deepcopy(relationship_instance)
            group_rel = (relationship_instance['type'] ==
                         GROUP_CONTAINED_IN_REL_TYPE)
            replaced = relationship_instance.pop('replaced', None)
            if replaced or group_rel:
                group_name = relationship_instance['target_name']
                group_id = relationship_instance['target_id']
                scaling_groups = [{
                    'name': group_name,
                    'id': group_id
                }]
                containing_groups, parent = ctx.containing_group_instances(
                    instance_id=group_id,
                    contained_graph=contained_graph
                )
                scaling_groups += containing_groups
                node_instance['scaling_groups'] = scaling_groups
                if replaced:
                    target_node_instance = parent
                    target_name = target_node_instance['name']
                    target_id = target_node_instance['id']
                    relationship_instance['target_name'] = target_name
                    relationship_instance['target_id'] = target_id
            if not group_rel:
                indexed_relationship_instances.append(
                    (relationship_index, relationship_instance))
        indexed_relationship_instances.sort(key=lambda (index, _): index)
        relationship_instances = [r for _, r in indexed_relationship_instances]
        node_instance[RELATIONSHIPS] = relationship_instances
        node_instances.append(node_instance)
    return node_instances


def extract_added_node_instances(previous_deployment_node_graph,
                                 new_deployment_node_graph,
                                 ctx):
    added_instances_graph = _graph_diff(
        new_deployment_node_graph,
        previous_deployment_node_graph,
        node_instance_attributes={'modification': 'added'})
    return extract_node_instances(
        added_instances_graph,
        ctx=ctx,
        copy_instances=True,
        contained_graph=ctx.deployment_contained_graph)


def extract_removed_node_instances(previous_deployment_node_graph,
                                   new_deployment_node_graph,
                                   ctx):
    removed_instances_graph = _graph_diff(
        previous_deployment_node_graph,
        new_deployment_node_graph,
        node_instance_attributes={'modification': 'removed'})
    return extract_node_instances(
        removed_instances_graph,
        ctx=ctx,
        copy_instances=True,
        contained_graph=ctx.previous_deployment_contained_graph)


def extract_added_relationships(previous_deployment_node_graph,
                                new_deployment_node_graph,
                                ctx):

    modified_instance_graph = _graph_diff_relationships(
        new_deployment_node_graph,
        previous_deployment_node_graph,
        node_instance_attributes={'modification': 'extended'})
    return extract_node_instances(
        modified_instance_graph,
        ctx=ctx,
        copy_instances=True,
        contained_graph=ctx.deployment_contained_graph)


def extract_removed_relationships(previous_deployment_node_graph,
                                  new_deployment_node_graph,
                                  ctx):
    modified_instance_graph = _graph_diff_relationships(
        previous_deployment_node_graph,
        new_deployment_node_graph,
        node_instance_attributes={'modification': 'reduced'})
    return extract_node_instances(
        modified_instance_graph,
        ctx=ctx,
        copy_instances=True,
        contained_graph=ctx.previous_deployment_contained_graph)


def _graph_diff(G, H, node_instance_attributes):
    result = nx.DiGraph()
    for n1, data in G.nodes_iter(data=True):
        if n1 in H:
            continue
        result.add_node(n1, data,
                        node_instance_attributes=node_instance_attributes)
        for n2 in G.neighbors_iter(n1):
            result.add_node(n2, G.node[n2])
            result.add_edge(n1, n2, G[n1][n2])
        for n2 in G.predecessors_iter(n1):
            result.add_node(n2, G.node[n2])
            result.add_edge(n2, n1, G[n2][n1])
    return result


def _graph_diff_relationships(G, H, node_instance_attributes):
    """
    G represents the base and H represents the changed graph.
    :param G:
    :param H:
    :param node_instance_attributes:
    :return:
    """
    result = nx.DiGraph()
    for source, dest, data in G.edges_iter(data=True):
        if source in H and dest not in H[source]:
            new_node = copy.deepcopy(G.node[source])
            result.add_node(source, new_node,
                            node_instance_attributes=node_instance_attributes)
            result.add_node(dest, G.node[dest])
            result.add_edge(source, dest, G[source][dest])
    return result


def _handle_contained_in(ctx):
    # for each 'contained' tree, recursively build new trees based on
    # scaling groups with generated ids
    for contained_tree in nx.weakly_connected_component_subgraphs(
            ctx.plan_contained_graph.reverse(copy=True)):
        # extract tree root node id
        node_id = nx.topological_sort(contained_tree)[0]
        _build_multi_instance_node_tree_rec(
            node_id=node_id,
            contained_tree=contained_tree,
            ctx=ctx)
    ctx.deployment_contained_graph = ctx.deployment_node_graph.copy()


def _build_multi_instance_node_tree_rec(node_id,
                                        contained_tree,
                                        ctx,
                                        parent_relationship=None,
                                        parent_relationship_index=None,
                                        parent_node_instance_id=None,
                                        current_host_instance_id=None):
    node = contained_tree.node[node_id]['node']
    containers = _build_and_update_node_instances(
        ctx=ctx,
        node=node,
        parent_node_instance_id=parent_node_instance_id,
        parent_relationship=parent_relationship,
        current_host_instance_id=current_host_instance_id)
    for container in containers:
        node_instance = container.node_instance
        node_instance_id = node_instance['id']
        relationship_instance = container.relationship_instance
        new_current_host_instance_id = container.current_host_instance_id
        ctx.deployment_node_graph.add_node(node_instance_id,
                                           node=node_instance)
        if parent_node_instance_id is not None:
            ctx.deployment_node_graph.add_edge(
                node_instance_id, parent_node_instance_id,
                relationship=relationship_instance,
                index=parent_relationship_index)
        for child_node_id in contained_tree.neighbors_iter(node_id):
            descendants = nx.descendants(contained_tree, child_node_id)
            descendants.add(child_node_id)
            child_contained_tree = contained_tree.subgraph(descendants)
            _build_multi_instance_node_tree_rec(
                node_id=child_node_id,
                contained_tree=child_contained_tree,
                ctx=ctx,
                parent_relationship=ctx.plan_node_graph[
                    child_node_id][node_id]['relationship'],
                parent_relationship_index=ctx.plan_node_graph[
                    child_node_id][node_id]['index'],
                parent_node_instance_id=node_instance_id,
                current_host_instance_id=new_current_host_instance_id)


def _build_and_update_node_instances(ctx,
                                     node,
                                     parent_node_instance_id,
                                     parent_relationship,
                                     current_host_instance_id):
    node_id = node['id']
    current_instances_num = ctx.plan_node_graph.node[node_id][
        'scale_properties']['current_instances']
    new_instances_num = 0
    previous_containers = []
    if ctx.is_modification:
        all_previous_node_instance_ids = ctx.node_ids_to_node_instance_ids[
            node_id]
        previous_node_instance_ids = [
            instance_id for instance_id in all_previous_node_instance_ids
            if not parent_node_instance_id or
            (instance_id in ctx.previous_deployment_node_graph and
             ctx.previous_deployment_node_graph[instance_id].get(
                 parent_node_instance_id))
        ]
        previous_instances_num = len(previous_node_instance_ids)
        if node_id in ctx.modified_nodes:
            modified_node = ctx.modified_nodes[node_id]
            total_instances_num = modified_node['instances']
            if total_instances_num > previous_instances_num:
                new_instances_num = (total_instances_num -
                                     previous_instances_num)
            else:
                # removed nodes are removed from the
                # 'previous_node_instance_ids' list which means they will
                # not be included in the resulting graph
                _handle_removed_instances(previous_node_instance_ids,
                                          previous_instances_num,
                                          total_instances_num,
                                          modified_node)
        else:
            new_instances_num = (current_instances_num -
                                 previous_instances_num)
        previous_node_instances = [
            ctx.previous_deployment_node_graph.node[node_instance_id]['node']
            for node_instance_id in previous_node_instance_ids]
        previous_containers = [Container(node_instance,
                                         _extract_contained(node,
                                                            node_instance),
                                         node_instance.get('host_id'))
                               for node_instance in previous_node_instances]
    else:
        new_instances_num = current_instances_num

    new_containers = []
    for _ in range(new_instances_num):
        node_instance_id = _node_instance_id(node_id, ctx)
        node_instance = _node_instance_copy(
            node=node,
            node_instance_id=node_instance_id)
        new_current_host_instance_id = _handle_host_instance_id(
            current_host_instance_id=current_host_instance_id,
            node_id=node_id,
            node_instance_id=node_instance_id,
            node_instance=node_instance)
        if parent_node_instance_id is not None:
            relationship_instance = _relationship_instance_copy(
                relationship=parent_relationship,
                target_node_instance_id=parent_node_instance_id)
        else:
            relationship_instance = None
        new_containers.append(Container(node_instance,
                                        relationship_instance,
                                        new_current_host_instance_id))
    return previous_containers + new_containers


def _handle_removed_instances(
        previous_node_instance_ids,
        previous_instances_num,
        total_instances_num,
        modified_node):
    removed_instances_num = previous_instances_num - total_instances_num
    removed_ids_include_hint = modified_node.get(
        'removed_ids_include_hint', [])
    removed_ids_exclude_hint = modified_node.get(
        'removed_ids_exclude_hint', [])
    for removed_instance_id in removed_ids_include_hint:
        if removed_instances_num <= 0:
            break
        if removed_instance_id in previous_node_instance_ids:
            previous_node_instance_ids.remove(removed_instance_id)
            removed_instances_num -= 1
    for removed_instance_id in copy.copy(
            previous_node_instance_ids):
        if removed_instances_num <= 0:
            break
        if removed_instance_id in removed_ids_exclude_hint:
            continue
        previous_node_instance_ids.remove(removed_instance_id)
        removed_instances_num -= 1
    remaining_removed_instance_ids = previous_node_instance_ids[
        :removed_instances_num]
    for removed_instance_id in remaining_removed_instance_ids:
        previous_node_instance_ids.remove(removed_instance_id)


def _extract_contained(node, node_instance):
    for node_relationship in node.get('relationships', []):
        if CONTAINED_IN_REL_TYPE in node_relationship['type_hierarchy']:
            contained_node_relationship = node_relationship
            break
    else:
        return None
    for node_instance_relationship in node_instance['relationships']:
        if (node_instance_relationship['type'] ==
                contained_node_relationship['type']):
            return node_instance_relationship
    raise RuntimeError("Failed extracting contained node instance "
                       "relationships for node instance '{0}'"
                       .format(node_instance['id']))


def _handle_host_instance_id(current_host_instance_id,
                             node_id,
                             node_instance_id,
                             node_instance):
    # If this condition applies, we assume current root is a host node
    if current_host_instance_id is None and \
       node_instance.get('host_id') == node_id:
        current_host_instance_id = node_instance_id
    if current_host_instance_id is not None:
        node_instance['host_id'] = current_host_instance_id
    return current_host_instance_id


def _handle_connected_to_and_depends_on(ctx):
    relationship_target_ids = _build_previous_target_ids_for_all_to_one(ctx)
    connected_graph = ctx.plan_connected_graph
    for source_node_id, target_node_id, edge_data in connected_graph.edges(
            data=True):
        relationship = edge_data['relationship']
        index = edge_data['index']
        connection_type = _verify_and_get_connection_type(relationship)
        source_node_instance_ids = ctx.node_ids_to_node_instance_ids[
            source_node_id]
        target_node_instance_ids = ctx.node_ids_to_node_instance_ids[
            target_node_id]
        _add_connected_to_and_depends_on_relationships(
            ctx=ctx,
            relationship=relationship,
            index=index,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            source_node_instance_ids=source_node_instance_ids,
            target_node_instance_ids=target_node_instance_ids,
            connection_type=connection_type,
            relationship_target_ids=relationship_target_ids)


def _build_previous_target_ids_for_all_to_one(ctx):
    relationship_target_ids = {}
    if ctx.is_modification:
        for s, t, e_data in ctx.previous_deployment_node_graph.edges_iter(
                data=True):
            s_node = ctx.previous_deployment_node_graph.node[s]['node']
            t_node = ctx.previous_deployment_node_graph.node[t]['node']
            rel = e_data['relationship']
            key = (_node_id_from_node_instance(s_node),
                   _node_id_from_node_instance(t_node),
                   rel['type'])
            if key not in relationship_target_ids:
                relationship_target_ids[key] = set()
            target_ids = relationship_target_ids[key]
            target_ids.add(rel['target_id'])
    return relationship_target_ids


def _get_all_to_one_relationship_target_id(
        ctx,
        relationship_target_ids,
        source_node_id,
        target_node_id,
        relationship,
        target_node_instance_ids):
    key = (source_node_id, target_node_id, relationship['type'])
    if ctx.is_modification and key in relationship_target_ids:
        target_ids = relationship_target_ids[key]
        if len(target_ids) != 1:
            raise exceptions.IllegalAllToOneState(
                    "Expected exactly one target id for relationship "
                    "{0}->{1} of type '{2}')".format(source_node_id,
                                                     target_node_id,
                                                     relationship['type']))
        return target_ids.copy().pop()
    else:
        return min(target_node_instance_ids)


def _add_connected_to_and_depends_on_relationships(
        ctx,
        relationship,
        index,
        source_node_id,
        target_node_id,
        source_node_instance_ids,
        target_node_instance_ids,
        connection_type,
        relationship_target_ids):
    if not source_node_instance_ids or not target_node_instance_ids:
        return

    minimal_containing_group = ctx.minimal_containing_group(
        node_a=source_node_id,
        node_b=target_node_id)

    if connection_type == ALL_TO_ONE:
        if minimal_containing_group:
            raise exceptions.UnsupportedAllToOneInGroup(
                "'{0}' connection type is not supported within groups, "
                "but the source node '{1}' and target node '{2}' are both in "
                "group '{3}'"
                .format(ALL_TO_ONE, source_node_id, target_node_id,
                        minimal_containing_group))
        else:
            target_node_instance_id = _get_all_to_one_relationship_target_id(
                ctx=ctx,
                relationship_target_ids=relationship_target_ids,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                relationship=relationship,
                target_node_instance_ids=target_node_instance_ids)
            target_node_instance_ids = [target_node_instance_id]

    if minimal_containing_group:
        partitioned_node_instance_ids = _partition_source_and_target_instances(
            ctx=ctx,
            group=minimal_containing_group,
            source_node_instance_ids=source_node_instance_ids,
            target_node_instance_ids=target_node_instance_ids)
    else:
        partitioned_node_instance_ids = [
            (source_node_instance_ids, target_node_instance_ids)]

    for source_node_instance_ids, target_node_instance_ids in \
            partitioned_node_instance_ids:
        for source_node_instance_id in source_node_instance_ids:
            for target_node_instance_id in target_node_instance_ids:
                relationship_instance = _relationship_instance_copy(
                    relationship=relationship,
                    target_node_instance_id=target_node_instance_id)
                ctx.deployment_node_graph.add_edge(
                    source_node_instance_id, target_node_instance_id,
                    relationship=relationship_instance,
                    index=index)


def _partition_source_and_target_instances(
        ctx,
        group,
        source_node_instance_ids,
        target_node_instance_ids):
    partitioned_node_instance_ids = []
    source_scaling_groups_map = _build_scaling_groups_map(
        ctx=ctx,
        node_instance_ids=source_node_instance_ids,
        group=group)
    target_scaling_groups_map = _build_scaling_groups_map(
        ctx=ctx,
        node_instance_ids=target_node_instance_ids,
        group=group)
    assert (set(source_scaling_groups_map.keys()) ==
            set(target_scaling_groups_map.keys()))
    for key, value in source_scaling_groups_map.items():
        partitioned_node_instance_ids.append((value,
                                              target_scaling_groups_map[key]))
    return partitioned_node_instance_ids


def _build_scaling_groups_map(ctx, node_instance_ids, group):
    node_instances = [ctx.deployment_node_graph.node[n]['node']
                      for n in node_instance_ids]
    scaling_groups_map = collections.defaultdict(list)
    for node_instance in node_instances:
        node_instance_id = node_instance['id']
        group_id = ctx.containing_group_id(
            node_instance_id=node_instance_id,
            group_name=group)
        if not group_id:
            raise RuntimeError('Unexpected state')
        scaling_groups_map[group_id].append(node_instance_id)
    return scaling_groups_map


def _node_instance_id(node_id, ctx):
    new_node_instance_id = '{0}_{1}'.format(node_id, _generate_id())
    while new_node_instance_id in ctx.node_instance_ids:
        new_node_instance_id = '{0}_{1}'.format(node_id, _generate_id())
    ctx.node_instance_ids.add(new_node_instance_id)
    return new_node_instance_id


def _generate_id():
    return '%05x' % random.randrange(16 ** 5)


def _node_instance_copy(node, node_instance_id):
    node_id = _node_id_from_node(node)
    result = {
        'name': node_id,
        'node_id': node_id,
        'id': node_instance_id
    }
    if 'host_id' in node:
        result['host_id'] = node['host_id']
    if node.get('group'):
        result['group'] = True
    return result


def _relationship_instance_copy(relationship,
                                target_node_instance_id):
    result = {
        'type': relationship['type'],
        'target_name': relationship['target_id'],
        'target_id': target_node_instance_id
    }
    replaced = relationship.get('replaced')
    if replaced:
        result['replaced'] = replaced
    return result


# currently we have decided not to support such relationships
# until we better understand what semantics are required for such
# relationships
def _verify_no_unsupported_relationships(graph):
    for s, t, edge in graph.edges_iter(data=True):
        if not _relationship_type_hierarchy_includes_one_of(
                edge['relationship'], [
                    DEPENDS_ON_REL_TYPE,
                    CONTAINED_IN_REL_TYPE,
                    CONNECTED_TO_REL_TYPE,
                    GROUP_CONTAINED_IN_REL_TYPE]):
            raise exceptions.UnsupportedRelationship()


def _verify_and_get_connection_type(relationship):
    connection_type = relationship.get('properties', {}).get(CONNECTION_TYPE)
    if connection_type not in [ALL_TO_ALL, ALL_TO_ONE]:
        raise exceptions.IllegalConnectedToConnectionType()
    return connection_type


def _relationship_type_hierarchy_includes_one_of(relationship, expected_types):
    relationship_type_hierarchy = relationship['type_hierarchy']
    return any([relationship_type in expected_types
                for relationship_type in relationship_type_hierarchy])


def _node_id_from_node(node):
    return node.get('name') or node.get('id')


def _node_id_from_node_instance(instance):
    return instance.get('name') or instance.get('node_id')


class Context(object):

    def __init__(self,
                 plan_node_graph,
                 deployment_node_graph,
                 previous_deployment_node_graph=None,
                 previous_deployment_contained_graph=None,
                 modified_nodes=None):
        self.plan_node_graph = plan_node_graph
        self.plan_contained_graph = self._build_contained_in_graph(
            plan_node_graph)
        self.plan_connected_graph = self._build_connected_to_and_depends_on_graph(  # noqa
            plan_node_graph)
        self.deployment_node_graph = deployment_node_graph
        self.deployment_contained_graph = None
        self.previous_deployment_node_graph = previous_deployment_node_graph
        self.previous_deployment_contained_graph = (
            previous_deployment_contained_graph)
        self.modified_nodes = modified_nodes
        self.node_ids_to_node_instance_ids = collections.defaultdict(set)
        self.node_instance_ids = set()
        if self.is_modification:
            for node_instance_id, data in \
                    self.previous_deployment_node_graph.nodes_iter(data=True):
                self.node_instance_ids.add(node_instance_id)
                node_instance = data['node']
                self.node_ids_to_node_instance_ids[
                    _node_id_from_node_instance(node_instance)].add(
                    node_instance_id)

    @property
    def is_modification(self):
        return self.previous_deployment_node_graph is not None

    def minimal_containing_group(self, node_a, node_b):
        a_groups = self._containing_groups(node_a)
        b_groups = self._containing_groups(node_b)
        shared_groups = set(a_groups) & set(b_groups)
        if not shared_groups:
            return None
        return nx.topological_sort(self.plan_contained_graph,
                                   nbunch=shared_groups)[0]

    def _containing_groups(self, node_id):
        graph = self.plan_contained_graph
        result = []
        while True:
            succ = graph.succ[node_id]
            if succ:
                assert len(succ) == 1
                node_id = succ.keys()[0]
                if not graph.node[node_id]['node'].get('group'):
                    continue
                result.append(node_id)
            else:
                break
        return result

    def containing_group_id(self, node_instance_id, group_name):
        graph = self.deployment_contained_graph
        while True:
            succ = graph.succ[node_instance_id]
            if succ:
                assert len(succ) == 1
                node_instance_id = succ.keys()[0]
                node = graph.node[node_instance_id]['node']
                if not node.get('group'):
                    continue
                if _node_id_from_node_instance(node) == group_name:
                    return node['id']
            else:
                return None

    @staticmethod
    def containing_group_instances(instance_id,
                                   contained_graph):
        result = []
        while True:
            succ = contained_graph.succ[instance_id]
            if succ:
                assert len(succ) == 1
                node_instance_id = succ.keys()[0]
                node = contained_graph.node[node_instance_id]['node']
                instance_id = node['id']
                result.append({
                    'name': _node_id_from_node_instance(node),
                    'id': instance_id
                })
                if not node.get('group'):
                    return result[:-1], result[-1]
            else:
                return result, None

    def restore_plan_node_graph(self):
        for _, data in self.plan_node_graph.nodes_iter(data=True):
            node = data['node']
            for relationship in node.get('relationships', []):
                replaced = relationship.pop('replaced', None)
                if replaced:
                    relationship['target_id'] = replaced

    def _build_connected_to_and_depends_on_graph(self, graph):
        return self._build_graph_by_relationship_types(
            graph,
            build_from_types=[CONNECTED_TO_REL_TYPE, DEPENDS_ON_REL_TYPE],
            # because contained_in derived from depends_on
            exclude_types=[CONTAINED_IN_REL_TYPE])

    def _build_contained_in_graph(self, graph):
        # build graph based only on connected_to relationships
        result = self._build_graph_by_relationship_types(
            graph,
            build_from_types=[CONTAINED_IN_REL_TYPE,
                              GROUP_CONTAINED_IN_REL_TYPE],
            exclude_types=[])
        # don't forget to include nodes in this graph that no one is contained
        # in them (these will be considered 1 node trees)
        result.add_nodes_from(graph.nodes_iter(data=True))
        return result

    @staticmethod
    def _build_graph_by_relationship_types(graph,
                                           build_from_types,
                                           exclude_types):
        relationship_base_graph = nx.DiGraph()
        for source, target, edge_data in graph.edges_iter(data=True):
            include_edge = (
                _relationship_type_hierarchy_includes_one_of(
                    edge_data['relationship'], build_from_types) and not
                _relationship_type_hierarchy_includes_one_of(
                    edge_data['relationship'], exclude_types))
            if include_edge:
                relationship_base_graph.add_node(source, graph.node[source])
                relationship_base_graph.add_node(target, graph.node[target])
                relationship_base_graph.add_edge(source, target, edge_data)
        return relationship_base_graph


class Container(object):

    def __init__(self,
                 node_instance,
                 relationship_instance,
                 current_host_instance_id):
        self.node_instance = node_instance
        self.relationship_instance = relationship_instance
        self.current_host_instance_id = current_host_instance_id
