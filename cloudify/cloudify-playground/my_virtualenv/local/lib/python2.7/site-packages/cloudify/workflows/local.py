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

import os
import tempfile
import copy
import importlib
import shutil
import uuid
import json
import threading
from contextlib import contextmanager

from cloudify_rest_client.nodes import Node
from cloudify_rest_client.node_instances import NodeInstance

from cloudify import dispatch
from cloudify.workflows.workflow_context import (
    DEFAULT_LOCAL_TASK_THREAD_POOL_SIZE)

try:
    from dsl_parser.constants import HOST_TYPE
    from dsl_parser import parser as dsl_parser, tasks as dsl_tasks
    from dsl_parser import functions as dsl_functions
    _import_error = None
except ImportError as e:
    _import_error = str(e)
    dsl_parser = None
    dsl_tasks = None
    dsl_functions = None
    HOST_TYPE = None


class _Environment(object):

    def __init__(self,
                 storage,
                 blueprint_path=None,
                 name='local',
                 inputs=None,
                 load_existing=False,
                 ignored_modules=None,
                 provider_context=None,
                 resolver=None,
                 validate_version=True):
        self.storage = storage
        self.storage.env = self

        if load_existing:
            self.storage.load(name)
        else:
            plan, nodes, node_instances = _parse_plan(blueprint_path,
                                                      inputs,
                                                      ignored_modules,
                                                      resolver,
                                                      validate_version)
            storage.init(
                name=name,
                plan=plan,
                nodes=nodes,
                node_instances=node_instances,
                blueprint_path=blueprint_path,
                provider_context=provider_context)

    @property
    def plan(self):
        return self.storage.plan

    @property
    def name(self):
        return self.storage.name

    def outputs(self):
        return dsl_functions.evaluate_outputs(
            outputs_def=self.plan['outputs'],
            get_node_instances_method=self.storage.get_node_instances,
            get_node_instance_method=self.storage.get_node_instance,
            get_node_method=self.storage.get_node)

    def evaluate_functions(self, payload, context):
        return dsl_functions.evaluate_functions(
            payload=payload,
            context=context,
            get_node_instances_method=self.storage.get_node_instances,
            get_node_instance_method=self.storage.get_node_instance,
            get_node_method=self.storage.get_node)

    def execute(self,
                workflow,
                parameters=None,
                allow_custom_parameters=False,
                task_retries=-1,
                task_retry_interval=30,
                subgraph_retries=0,
                task_thread_pool_size=DEFAULT_LOCAL_TASK_THREAD_POOL_SIZE):
        workflows = self.plan['workflows']
        workflow_name = workflow
        if workflow_name not in workflows:
            raise ValueError("'{0}' workflow does not exist. "
                             "existing workflows are: {1}"
                             .format(workflow_name,
                                     workflows.keys()))

        workflow = workflows[workflow_name]
        execution_id = str(uuid.uuid4())
        ctx = {
            'type': 'workflow',
            'local': True,
            'deployment_id': self.name,
            'blueprint_id': self.name,
            'execution_id': execution_id,
            'workflow_id': workflow_name,
            'storage': self.storage,
            'task_retries': task_retries,
            'task_retry_interval': task_retry_interval,
            'subgraph_retries': subgraph_retries,
            'local_task_thread_pool_size': task_thread_pool_size,
            'task_name': workflow['operation']
        }

        merged_parameters = _merge_and_validate_execution_parameters(
            workflow, workflow_name, parameters, allow_custom_parameters)

        return dispatch.dispatch(__cloudify_context=ctx, **merged_parameters)


def init_env(blueprint_path,
             name='local',
             inputs=None,
             storage=None,
             ignored_modules=None,
             provider_context=None,
             resolver=None,
             validate_version=True):
    if storage is None:
        storage = InMemoryStorage()
    return _Environment(storage=storage,
                        blueprint_path=blueprint_path,
                        name=name,
                        inputs=inputs,
                        load_existing=False,
                        ignored_modules=ignored_modules,
                        provider_context=provider_context,
                        resolver=resolver,
                        validate_version=validate_version)


def load_env(name, storage, resolver=None):
    return _Environment(storage=storage,
                        name=name,
                        load_existing=True,
                        resolver=resolver)


def _parse_plan(blueprint_path, inputs, ignored_modules, resolver,
                validate_version):
    if dsl_parser is None:
        raise ImportError('cloudify-dsl-parser must be installed to '
                          'execute local workflows. '
                          '(e.g. "pip install cloudify-dsl-parser") [{0}]'
                          .format(_import_error))
    plan = dsl_tasks.prepare_deployment_plan(
        dsl_parser.parse_from_path(
            dsl_file_path=blueprint_path,
            resolver=resolver,
            validate_version=validate_version),
        inputs=inputs)
    nodes = [Node(node) for node in plan['nodes']]
    node_instances = [NodeInstance(instance)
                      for instance in plan['node_instances']]
    _prepare_nodes_and_instances(nodes, node_instances, ignored_modules)
    return plan, nodes, node_instances


def _validate_node(node):
    if HOST_TYPE in node['type_hierarchy']:
        install_agent_prop = node.properties.get('install_agent')
        if install_agent_prop:
            raise ValueError("'install_agent': true is not supported "
                             "(it is True by default) "
                             "when executing local workflows. "
                             "The 'install_agent' property "
                             "must be set to false for each node of type {0}."
                             .format(HOST_TYPE))


def _prepare_nodes_and_instances(nodes, node_instances, ignored_modules):

    def scan(parent, name, node):
        for operation in parent.get(name, {}).values():
            if not operation['operation']:
                continue
            _get_module_method(operation['operation'],
                               tpe=name,
                               node_name=node.id,
                               ignored_modules=ignored_modules)

    for node in nodes:
        scalable = node['capabilities']['scalable']['properties']
        node.update(dict(
            number_of_instances=scalable['current_instances'],
            deploy_number_of_instances=scalable['default_instances'],
            min_number_of_instances=scalable['min_instances'],
            max_number_of_instances=scalable['max_instances'],
        ))
        if 'relationships' not in node:
            node['relationships'] = []
        scan(node, 'operations', node)
        _validate_node(node)
        for relationship in node['relationships']:
            scan(relationship, 'source_operations', node)
            scan(relationship, 'target_operations', node)

    for node_instance in node_instances:
        node_instance['version'] = 0
        node_instance['runtime_properties'] = {}
        node_instance['node_id'] = node_instance['name']
        if 'relationships' not in node_instance:
            node_instance['relationships'] = []


def _get_module_method(module_method_path, tpe, node_name,
                       ignored_modules=None):
    ignored_modules = ignored_modules or []
    split = module_method_path.split('.')
    module_name = '.'.join(split[:-1])
    if module_name in ignored_modules:
        return None
    method_name = split[-1]
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        raise ImportError('mapping error: No module named {0} '
                          '[node={1}, type={2}]'
                          .format(module_name, node_name, tpe))
    try:
        return getattr(module, method_name)
    except AttributeError:
        raise AttributeError("mapping error: {0} has no attribute '{1}' "
                             "[node={2}, type={3}]"
                             .format(module.__name__, method_name,
                                     node_name, tpe))


def _merge_and_validate_execution_parameters(
        workflow, workflow_name, execution_parameters=None,
        allow_custom_parameters=False):

    merged_parameters = {}
    workflow_parameters = workflow.get('parameters', {})
    execution_parameters = execution_parameters or {}

    missing_mandatory_parameters = set()

    for name, param in workflow_parameters.iteritems():
        if 'default' not in param:
            if name not in execution_parameters:
                missing_mandatory_parameters.add(name)
                continue
            merged_parameters[name] = execution_parameters[name]
        else:
            merged_parameters[name] = execution_parameters[name] if \
                name in execution_parameters else param['default']

    if missing_mandatory_parameters:
        raise ValueError(
            'Workflow "{0}" must be provided with the following '
            'parameters to execute: {1}'
            .format(workflow_name, ','.join(missing_mandatory_parameters)))

    custom_parameters = dict(
        (k, v) for (k, v) in execution_parameters.iteritems()
        if k not in workflow_parameters)

    if not allow_custom_parameters and custom_parameters:
        raise ValueError(
            'Workflow "{0}" does not have the following parameters '
            'declared: {1}. Remove these parameters or use '
            'the flag for allowing custom parameters'
            .format(workflow_name, ','.join(custom_parameters.keys())))

    merged_parameters.update(custom_parameters)
    return merged_parameters


class _Storage(object):

    def __init__(self):
        self.name = None
        self.resources_root = None
        self.plan = None
        self._nodes = None
        self._locks = None
        self.env = None
        self._provider_context = None

    def init(self, name, plan, nodes, node_instances, blueprint_path,
             provider_context):
        self.name = name
        self.resources_root = os.path.dirname(os.path.abspath(blueprint_path))
        self.plan = plan
        self._provider_context = provider_context or {}
        self._init_locks_and_nodes(nodes)

    def _init_locks_and_nodes(self, nodes):
        self._nodes = dict((node.id, node) for node in nodes)
        self._locks = dict((instance_id, threading.RLock()) for instance_id
                           in self._instance_ids())

    def load(self, name):
        raise NotImplementedError()

    def get_resource(self, resource_path):
        with open(os.path.join(self.resources_root, resource_path)) as f:
            return f.read()

    def download_resource(self, resource_path, target_path=None):
        if not target_path:
            suffix = '-{0}'.format(os.path.basename(resource_path))
            target_path = tempfile.mktemp(suffix=suffix)
        resource = self.get_resource(resource_path)
        with open(target_path, 'wb') as f:
            f.write(resource)
        return target_path

    def update_node_instance(self,
                             node_instance_id,
                             version,
                             runtime_properties=None,
                             state=None):
        with self._lock(node_instance_id):
            instance = self._get_node_instance(node_instance_id)
            if state is None and version != instance['version']:
                raise StorageConflictError('version {0} does not match '
                                           'current version of '
                                           'node instance {1} which is {2}'
                                           .format(version,
                                                   node_instance_id,
                                                   instance['version']))
            else:
                instance['version'] += 1
            if runtime_properties is not None:
                instance['runtime_properties'] = runtime_properties
            if state is not None:
                instance['state'] = state
            self._store_instance(instance)

    def _get_node_instance(self, node_instance_id):
        instance = self._load_instance(node_instance_id)
        if instance is None:
            raise RuntimeError('Instance {0} does not exist'
                               .format(node_instance_id))
        return instance

    def get_node(self, node_id):
        node = self._nodes.get(node_id)
        if node is None:
            raise RuntimeError('Node {0} does not exist'
                               .format(node_id))
        return copy.deepcopy(node)

    def get_nodes(self):
        return copy.deepcopy(self._nodes.values())

    def get_node_instance(self, node_instance_id):
        return copy.deepcopy(self._get_node_instance(node_instance_id))

    def get_provider_context(self):
        return copy.deepcopy(self._provider_context)

    def _load_instance(self, node_instance_id):
        raise NotImplementedError()

    def _store_instance(self, node_instance):
        raise NotImplementedError()

    def get_node_instances(self, node_id=None):
        raise NotImplementedError()

    def _instance_ids(self):
        raise NotImplementedError()

    def _lock(self, node_instance_id):
        return self._locks[node_instance_id]

    def get_workdir(self):
        raise NotImplementedError()


class InMemoryStorage(_Storage):

    def __init__(self):
        super(InMemoryStorage, self).__init__()
        self._node_instances = None

    def init(self, name, plan, nodes, node_instances, blueprint_path,
             provider_context):
        self.plan = plan
        self._node_instances = dict((instance.id, instance)
                                    for instance in node_instances)
        super(InMemoryStorage, self).init(name, plan, nodes, node_instances,
                                          blueprint_path, provider_context)

    def load(self, name):
        raise NotImplementedError('load is not implemented by memory storage')

    def _load_instance(self, node_instance_id):
        return self._node_instances.get(node_instance_id)

    def _store_instance(self, node_instance):
        pass

    def get_node_instances(self, node_id=None):
        instances = self._node_instances.values()
        if node_id:
            instances = [i for i in instances if i.node_id == node_id]
        return copy.deepcopy(instances)

    def _instance_ids(self):
        return self._node_instances.keys()

    def get_workdir(self):
        raise NotImplementedError('get_workdir is not implemented by memory '
                                  'storage')


class FileStorage(_Storage):

    def __init__(self, storage_dir='/tmp/cloudify-workflows'):
        super(FileStorage, self).__init__()
        self._root_storage_dir = os.path.join(storage_dir)
        self._storage_dir = None
        self._workdir = None
        self._instances_dir = None
        self._data_path = None
        self._payload_path = None
        self._blueprint_path = None

    def init(self, name, plan, nodes, node_instances, blueprint_path,
             provider_context):
        storage_dir = os.path.join(self._root_storage_dir, name)
        workdir = os.path.join(storage_dir, 'work')
        instances_dir = os.path.join(storage_dir, 'node-instances')
        data_path = os.path.join(storage_dir, 'data')
        payload_path = os.path.join(storage_dir, 'payload')
        os.makedirs(storage_dir)
        os.mkdir(instances_dir)
        os.mkdir(workdir)
        with open(payload_path, 'w') as f:
            f.write(json.dumps({}))

        blueprint_filename = os.path.basename(os.path.abspath(blueprint_path))
        with open(data_path, 'w') as f:
            f.write(json.dumps({
                'plan': plan,
                'blueprint_filename': blueprint_filename,
                'nodes': nodes,
                'provider_context': provider_context or {}
            }))
        resources_root = os.path.dirname(os.path.abspath(blueprint_path))
        self.resources_root = os.path.join(storage_dir, 'resources')

        def ignore(src, names):
            return names if os.path.abspath(self.resources_root) == src \
                else set()
        shutil.copytree(resources_root, self.resources_root, ignore=ignore)
        self._instances_dir = instances_dir
        for instance in node_instances:
            self._store_instance(instance, lock=False)
        self.load(name)

    def load(self, name):
        self.name = name
        self._storage_dir = os.path.join(self._root_storage_dir, name)
        self._workdir = os.path.join(self._storage_dir, 'workdir')
        self._instances_dir = os.path.join(self._storage_dir, 'node-instances')
        self._payload_path = os.path.join(self._storage_dir, 'payload')
        self._data_path = os.path.join(self._storage_dir, 'data')
        with open(self._data_path) as f:
            data = json.loads(f.read())
        self.plan = data['plan']
        self.resources_root = os.path.join(self._storage_dir, 'resources')
        self._blueprint_path = os.path.join(self.resources_root,
                                            data['blueprint_filename'])
        self._provider_context = data.get('provider_context', {})
        nodes = [Node(node) for node in data['nodes']]
        self._init_locks_and_nodes(nodes)

    @contextmanager
    def payload(self):
        with open(self._payload_path, 'r') as f:
            payload = json.load(f)
            yield payload
        with open(self._payload_path, 'w') as f:
            json.dump(payload, f, indent=2)
            f.write(os.linesep)

    def get_blueprint_path(self):
        return self._blueprint_path

    def get_node_instance(self, node_instance_id):
        return self._get_node_instance(node_instance_id)

    def _load_instance(self, node_instance_id):
        with self._lock(node_instance_id):
            with open(self._instance_path(node_instance_id)) as f:
                return NodeInstance(json.loads(f.read()))

    def _store_instance(self, node_instance, lock=True):
        instance_lock = None
        if lock:
            instance_lock = self._lock(node_instance.id)
            instance_lock.acquire()
        try:
            with open(self._instance_path(node_instance.id), 'w') as f:
                f.write(json.dumps(node_instance))
        finally:
            if lock and instance_lock:
                instance_lock.release()

    def _instance_path(self, node_instance_id):
        return os.path.join(self._instances_dir, node_instance_id)

    def get_node_instances(self, node_id=None):
        instances = [self._get_node_instance(instance_id)
                     for instance_id in self._instance_ids()]
        if node_id:
            instances = [i for i in instances if i.node_id == node_id]
        return instances

    def _instance_ids(self):
        return os.listdir(self._instances_dir)

    def get_workdir(self):
        return self._workdir


class StorageConflictError(Exception):
    pass
