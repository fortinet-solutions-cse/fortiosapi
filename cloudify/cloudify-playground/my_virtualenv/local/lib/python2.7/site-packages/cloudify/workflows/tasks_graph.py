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
import json
import time

import networkx as nx

from cloudify.workflows import api
from cloudify.workflows import tasks


class TaskDependencyGraph(object):
    """
    A task graph builder

    :param workflow_context: A WorkflowContext instance (used for logging)
    """

    def __init__(self, workflow_context,
                 default_subgraph_task_config=None):
        self.ctx = workflow_context
        self.graph = nx.DiGraph()
        default_subgraph_task_config = default_subgraph_task_config or {}
        self._default_subgraph_task_config = default_subgraph_task_config

    def add_task(self, task):
        """Add a WorkflowTask to this graph

        :param task: The task
        """
        self.graph.add_node(task.id, task=task)

    def get_task(self, task_id):
        """Get a task instance that was inserted to this graph by its id

        :param task_id: the task id
        :return: a WorkflowTask instance for the requested task if found.
                 None, otherwise.
        """
        data = self.graph.node.get(task_id)
        return data['task'] if data is not None else None

    def remove_task(self, task):
        """Remove the provided task from the graph

        :param task: The task
        """
        if task.is_subgraph:
            for subgraph_task in task.tasks.values():
                self.remove_task(subgraph_task)
        if task.id in self.graph:
            self.graph.remove_node(task.id)

    # src depends on dst
    def add_dependency(self, src_task, dst_task):
        """
        Add a dependency between tasks.
        The source task will only be executed after the target task terminates.
        A task may depend on several tasks, in which case it will only be
        executed after all its 'destination' tasks terminate

        :param src_task: The source task
        :param dst_task: The target task
        """
        if not self.graph.has_node(src_task.id):
            raise RuntimeError('source task {0} is not in graph (task id: '
                               '{1})'.format(src_task, src_task.id))
        if not self.graph.has_node(dst_task.id):
            raise RuntimeError('destination task {0} is not in graph (task '
                               'id: {1})'.format(dst_task, dst_task.id))
        self.graph.add_edge(src_task.id, dst_task.id)

    def sequence(self):
        """
        :return: a new TaskSequence for this graph
        """
        return TaskSequence(self)

    def subgraph(self, name):
        task = SubgraphTask(name, self, **self._default_subgraph_task_config)
        self.add_task(task)
        return task

    def execute(self):
        """
        Start executing the graph based on tasks and dependencies between
        them.
        Calling this method will block until one of the following occurs:
            1. all tasks terminated
            2. a task failed
            3. an unhandled exception is raised
            4. the execution is cancelled

        Note: This method will raise an api.ExecutionCancelled error if the
        execution has been cancelled. When catching errors raised from this
        method, make sure to re-raise the error if it's
        api.ExecutionsCancelled in order to allow the execution to be set in
        cancelled mode properly.

        Also note that for the time being, if such a cancelling event
        occurs, the method might return even while there's some operations
        still being executed.
        """

        while True:

            if self._is_execution_cancelled():
                raise api.ExecutionCancelled()

            self._check_dump_request()

            # handle all terminated tasks
            # it is important this happens before handling
            # executable tasks so we get to make tasks executable
            # and then execute them in this iteration (otherwise, it would
            # be the next one)
            for task in self._terminated_tasks():
                self._handle_terminated_task(task)

            # handle all executable tasks
            for task in self._executable_tasks():
                self._handle_executable_task(task)

            # no more tasks to process, time to move on
            if len(self.graph.node) == 0:
                return
            # sleep some and do it all over again
            else:
                time.sleep(0.1)

    @staticmethod
    def _is_execution_cancelled():
        return api.has_cancel_request()

    def _executable_tasks(self):
        """
        A task is executable if it is in pending state
        , it has no dependencies at the moment (i.e. all of its dependencies
        already terminated) and its execution timestamp is smaller then the
        current timestamp

        :return: An iterator for executable tasks
        """
        now = time.time()
        return (task for task in self.tasks_iter()
                if task.get_state() == tasks.TASK_PENDING and
                task.execute_after <= now and
                not (task.containing_subgraph and
                     task.containing_subgraph.get_state() ==
                     tasks.TASK_FAILED) and
                not self._task_has_dependencies(task))

    def _terminated_tasks(self):
        """
        A task is terminated if it is in 'succeeded' or 'failed' state

        :return: An iterator for terminated tasks
        """
        return (task for task in self.tasks_iter()
                if task.get_state() in tasks.TERMINATED_STATES)

    def _task_has_dependencies(self, task):
        """
        :param task: The task
        :return: Does this task have any dependencies
        """
        return (len(self.graph.succ.get(task.id, {})) > 0 or
                (task.containing_subgraph and self._task_has_dependencies(
                    task.containing_subgraph)))

    def tasks_iter(self):
        """
        An iterator on tasks added to the graph
        """
        return (data['task'] for _, data in self.graph.nodes_iter(data=True))

    def _handle_executable_task(self, task):
        """Handle executable task"""
        task.set_state(tasks.TASK_SENDING)
        task.apply_async()

    def _handle_terminated_task(self, task):
        """Handle terminated task"""

        handler_result = task.handle_task_terminated()
        if handler_result.action == tasks.HandlerResult.HANDLER_FAIL:
            if isinstance(task, SubgraphTask) and task.failed_task:
                task = task.failed_task
            message = "Workflow failed: Task failed '{0}'".format(task.name)
            if task.error:
                message = '{0} -> {1}'.format(message, task.error)
            raise RuntimeError(message)

        dependents = self.graph.predecessors(task.id)
        removed_edges = [(dependent, task.id)
                         for dependent in dependents]
        self.graph.remove_edges_from(removed_edges)
        self.graph.remove_node(task.id)
        if handler_result.action == tasks.HandlerResult.HANDLER_RETRY:
            new_task = handler_result.retried_task
            self.add_task(new_task)
            added_edges = [(dependent, new_task.id)
                           for dependent in dependents]
            self.graph.add_edges_from(added_edges)

    def _check_dump_request(self):
        task_dump = os.environ.get('WORKFLOW_TASK_DUMP')
        if not (task_dump and os.path.exists(task_dump)):
            return
        os.remove(task_dump)
        task_dump_path = '{0}.{1}'.format(task_dump, time.time())
        with open(task_dump_path, 'w') as f:
            f.write(json.dumps({
                'tasks': [task.dump() for task in self.tasks_iter()],
                'edges': [[s, t] for s, t in self.graph.edges_iter()]}))


class forkjoin(object):
    """
    A simple wrapper for tasks. Used in conjunction with TaskSequence.
    Defined to make the code easier to read (instead of passing a list)
    see ``TaskSequence.add`` for more details
    """

    def __init__(self, *tasks):
        self.tasks = tasks


class TaskSequence(object):
    """
    Helper class to add tasks in a sequential manner to a task dependency
    graph

    :param graph: The TaskDependencyGraph instance
    """

    def __init__(self, graph):
        self.graph = graph
        self.last_fork_join_tasks = None

    def add(self, *tasks):
        """
        Add tasks to the sequence.

        :param tasks: Each task might be:

                      * A WorkflowTask instance, in which case, it will be
                        added to the graph with a dependency between it and
                        the task previously inserted into the sequence
                      * A forkjoin of tasks, in which case it will be treated
                        as a "fork-join" task in the sequence, i.e. all the
                        fork-join tasks will depend on the last task in the
                        sequence (could be fork join) and the next added task
                        will depend on all tasks in this fork-join task
        """
        for fork_join_tasks in tasks:
            if isinstance(fork_join_tasks, forkjoin):
                fork_join_tasks = fork_join_tasks.tasks
            else:
                fork_join_tasks = [fork_join_tasks]
            for task in fork_join_tasks:
                self.graph.add_task(task)
                if self.last_fork_join_tasks is not None:
                    for last_fork_join_task in self.last_fork_join_tasks:
                        self.graph.add_dependency(task, last_fork_join_task)
            if fork_join_tasks:
                self.last_fork_join_tasks = fork_join_tasks


class SubgraphTask(tasks.WorkflowTask):

    def __init__(self,
                 name,
                 graph,
                 task_id=None,
                 on_success=None,
                 on_failure=None,
                 total_retries=tasks.DEFAULT_SUBGRAPH_TOTAL_RETRIES,
                 retry_interval=tasks.DEFAULT_RETRY_INTERVAL,
                 send_task_events=tasks.DEFAULT_SEND_TASK_EVENTS):
        super(SubgraphTask, self).__init__(
            graph.ctx,
            task_id,
            info=name,
            on_success=on_success,
            on_failure=on_failure,
            total_retries=total_retries,
            retry_interval=retry_interval,
            send_task_events=send_task_events)
        self.graph = graph
        self._name = name
        self.tasks = {}
        self.failed_task = None
        if not self.on_failure:
            self.on_failure = lambda tsk: tasks.HandlerResult.fail()
        self.async_result = tasks.StubAsyncResult()

    def _duplicate(self):
        raise NotImplementedError('self.retried_task should be set explicitly'
                                  ' in self.on_failure handler')

    @property
    def cloudify_context(self):
        return {}

    def is_local(self):
        return True

    @property
    def name(self):
        return self._name

    @property
    def is_subgraph(self):
        return True

    def sequence(self):
        return TaskSequence(self)

    def subgraph(self, name):
        task = SubgraphTask(name, self.graph,
                            **self.graph._default_subgraph_task_config)
        self.add_task(task)
        return task

    def add_task(self, task):
        self.graph.add_task(task)
        self.tasks[task.id] = task
        if task.containing_subgraph and task.containing_subgraph is not self:
            raise RuntimeError('task {0}[{1}] cannot be contained in more '
                               'than one subgraph. It is currently contained '
                               'in {2} and it is now being added to {3}'
                               .format(task,
                                       task.id,
                                       task.containing_subgraph.name,
                                       self.name))
        task.containing_subgraph = self

    def remove_task(self, task):
        self.graph.remove_task(task)

    def add_dependency(self, src_task, dst_task):
        self.graph.add_dependency(src_task, dst_task)

    def apply_async(self):
        if not self.tasks:
            self.set_state(tasks.TASK_SUCCEEDED)
        else:
            self.set_state(tasks.TASK_STARTED)

    def task_terminated(self, task, new_task=None):
        del self.tasks[task.id]
        if new_task:
            self.tasks[new_task.id] = new_task
            new_task.containing_subgraph = self
        if not self.tasks and self.get_state() not in tasks.TERMINATED_STATES:
            self.set_state(tasks.TASK_SUCCEEDED)
