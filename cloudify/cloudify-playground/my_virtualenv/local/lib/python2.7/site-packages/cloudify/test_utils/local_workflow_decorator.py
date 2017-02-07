#########
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
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

import sys
import shutil
import tempfile
from os import path, listdir, makedirs
from functools import wraps

from cloudify.workflows import local

PLUGIN_YAML_NAME = 'plugin.yaml'

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'cloudify_agent.operations',
    'cloudify_agent.installer.operations',

    # maintained for backward compatibily with < 3.3 blueprints
    'worker_installer.tasks',
    'plugin_installer.tasks',
    'windows_agent_installer.tasks',
    'windows_plugin_installer.tasks'
)


def _find_plugin_yaml(original_path):
    """
    Tries to find the plugin.yaml file automatically (by traversing up the
    directory tree).
    :param original_path: The path to start the search from
    :return: The absolute path of the plugin.yaml file (if found, o.w. raises
     an Error)
    """
    running_path = original_path
    while PLUGIN_YAML_NAME not in listdir(running_path):
        level_up_path = path.dirname(running_path)
        if level_up_path == running_path:
            msg = 'Traversing up the folder tree from {0}, failed to find {1}.'
            raise IOError(msg.format(original_path, PLUGIN_YAML_NAME))
        else:
            running_path = level_up_path

    return path.abspath(path.join(running_path, PLUGIN_YAML_NAME))


def _assure_path_exists(dest_path):
    """
    Creates a the destination path (if not exists)
    :param dest_path:
    :return:
    """
    dir_path = path.dirname(dest_path)
    if not path.exists(dir_path):
        makedirs(dir_path)


def _expand_dictionary(inputs, func_self, func_args, func_kwargs):
    func_to_call = None
    if callable(inputs):
        func_to_call = inputs
    elif isinstance(inputs, basestring):
        if func_self is None:
            raise ValueError("You cannot supply 'string' "
                             "references to 'self' object in "
                             "contextmanager mode.")
        else:
            func_to_call = getattr(func_self, inputs)

    if func_to_call:
        return func_to_call(*func_args, **func_kwargs)

    return inputs


def _copy_resources(test_source_path, resources, default_dest_path):
    """
    Copies a list of resources to the dest_path

    :param test_source_path: the default destination path
    :param resources: a list of resources to be copied - can contain source
    path only, or a tuple of source and destination path.
    :return: None
    """
    for resource in resources:
        # Setting resource relative destination path and temp source path
        if isinstance(resource, tuple):
            resource_source_path, relative_dest_path = resource
            relative_dest_path = path.join(relative_dest_path,
                                           path.basename(resource_source_path))
        else:
            resource_source_path = resource
            relative_dest_path = path.basename(resource_source_path)

        # Setting resource source path
        if test_source_path:
            if not path.isabs(resource_source_path):
                resource_source_path = path.join(test_source_path,
                                                 resource_source_path)

        # Setting absolute destination path
        resource_dest_path = path.join(default_dest_path, relative_dest_path)

        _assure_path_exists(path.dirname(resource_dest_path))
        shutil.copyfile(resource_source_path, resource_dest_path)


class WorkflowTestDecorator(object):
    def __init__(self,
                 blueprint_path,
                 copy_plugin_yaml=False,
                 resources_to_copy=None,
                 temp_dir_prefix=None,
                 init_args=None,
                 inputs=None,
                 input_func_args=None,
                 input_func_kwargs=None):
        """
        Sets the required parameters for future env init. passes the
        environment to the cfy_local argument.

        :param blueprint_path: The relative path to the blueprint
        :param copy_plugin_yaml: Tries to find and copy plugin.yaml (optional)
        :param resources_to_copy: Paths to resources to copy (optional)
        :param temp_dir_prefix: prefix for the resources (optional)
        :param init_args: arguments to pass to the environment init (optional).
        :param inputs: directs inputs assignments into init_args0 (optional).
        :param input_func_args: if you pass a function name into the inputs,
               you can use this arg to specify the args to the function.
        :param input_func_kwargs: if you pass a function name into the inputs,
               you can use this arg to specify the kwargs to the function.
        """

        # blueprint to run
        self.blueprint_path = blueprint_path
        self.temp_blueprint_path = None

        # Plugin path and name
        self.resources_to_copy = resources_to_copy if resources_to_copy else []

        self.copy_plugin_yaml = copy_plugin_yaml
        if self.copy_plugin_yaml:
            self.plugin_yaml_filename = PLUGIN_YAML_NAME

        # Set prefix for resources
        self.temp_dir_prefix = temp_dir_prefix
        self.temp_dir = None

        # set init args
        if init_args:
            self.init_args = init_args
            if 'ignored_modules' not in init_args:
                self.init_args['ignored_modules'] = \
                    IGNORED_LOCAL_WORKFLOW_MODULES
        else:
            self.init_args = {
                'ignored_modules': IGNORED_LOCAL_WORKFLOW_MODULES
            }

        # set the inputs (if set)
        if inputs and 'inputs' in self.init_args.keys():
            raise ValueError("You've supplied 'inputs' inside init_args and as"
                             " a keyword. You cannot have more than "
                             "1 'inputs' source is needed.")
        else:
            if inputs:
                self.init_args['inputs'] = inputs
        self.input_func_args = input_func_args or []
        self.input_func_kwargs = input_func_kwargs or {}

    def set_up(self, func_self=None):
        """
        Sets up the enviroment variables needed for this test.

        :param local_file_path: the path of the test file.
        :param test_method_name: the name of the test method.
        :return: The test env which is a wrapped Environment.
        """
        if func_self:
            local_file_path = \
                sys.modules[func_self.__class__.__module__].__file__
            test_method_name = func_self._testMethodName
        else:
            local_file_path, test_method_name = None, None

        # Creating a temp dir
        if self.temp_dir_prefix:
            self.temp_dir = tempfile.mkdtemp(prefix=self.temp_dir_prefix)
        elif test_method_name:
            self.temp_dir = tempfile.mkdtemp(prefix=test_method_name)
        else:
            self.temp_dir = tempfile.mkdtemp()

        # Adding blueprint to the resources to copy
        self.resources_to_copy.append(self.blueprint_path)

        # Finding and adding the plugin
        if func_self is not None and self.copy_plugin_yaml:
            self.resources_to_copy.append(
                _find_plugin_yaml(path.dirname(local_file_path)))
        elif self.copy_plugin_yaml:
            raise StandardError("You cannot use copy_plugin_yaml in "
                                "contextmanager mode.")

        # Copying resources
        _copy_resources(path.dirname(local_file_path)
                        if local_file_path else None,
                        self.resources_to_copy, self.temp_dir)

        # Updating the test_method_name (if not manually set)
        if self.init_args and not self.init_args.get('name'):
            self.init_args['name'] = test_method_name

        # Expand inputs dictionary
        if 'inputs' in self.init_args.keys():
            self.input_func_kwargs['decorator_kwargs'] = vars(self)
            self.init_args['inputs'] = \
                _expand_dictionary(self.init_args['inputs'],
                                   func_self,
                                   self.input_func_args,
                                   self.input_func_kwargs)

        # Init env with supplied args
        temp_blueprint_path = path.join(self.temp_dir,
                                        path.basename(self.blueprint_path))
        test_env = local.init_env(temp_blueprint_path, **self.init_args)

        return test_env

    def tear_down(self):
        """
        Deletes the allocated temp dir
        :return: None
        """
        if path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def __call__(self, test):
        @wraps(test)
        def wrapped_test(func_self, *args, **kwargs):
            """
            The wrapper function itself.

            :param func: the function of which this test has been called from
            :return:
            """
            test_env = self.set_up(func_self)
            try:
                test(func_self, test_env, *args, **kwargs)
            finally:
                self.tear_down()

        return wrapped_test

    # Support for context manager
    def __enter__(self):
        return self.set_up()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tear_down()
