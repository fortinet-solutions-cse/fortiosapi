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

import logging
import os
import random
import shlex
import ssl
import string
import subprocess
import sys
import tempfile
import traceback
import StringIO

from cloudify import constants
from cloudify.exceptions import (
    CommandExecutionException,
    NonRecoverableError,
)


class ManagerVersion(object):
    """Cloudify manager version helper class."""

    def __init__(self, raw_version):
        """Raw version, for example: 3.4.0-m1, 3.3, 3.2.1, 3.3-rc1."""

        components = [int(x) for x in raw_version.split('-')[0].split('.')]
        if len(components) == 2:
            components.append(0)
        self.major = components[0]
        self.minor = components[1]
        self.service = components[2]

    def greater_than(self, other):
        """Returns true if this version is greater than the provided one."""

        if self.major > other.major:
            return True
        if self.major == other.major:
            if self.minor > other.minor:
                return True
            if self.minor == other.minor and self.service > other.service:
                return True
        return False

    def equals(self, other):
        """Returns true if this version equals the provided version."""
        return self.major == other.major and self.minor == other.minor and \
            self.service == other.service

    def __str__(self):
        return '{0}.{1}.{2}'.format(self.major, self.minor, self.service)


def setup_logger(logger_name,
                 logger_level=logging.INFO,
                 handlers=None,
                 remove_existing_handlers=True,
                 logger_format=None,
                 propagate=True):
    """
    :param logger_name: Name of the logger.
    :param logger_level: Level for the logger (not for specific handler).
    :param handlers: An optional list of handlers (formatter will be
                     overridden); If None, only a StreamHandler for
                     sys.stdout will be used.
    :param remove_existing_handlers: Determines whether to remove existing
                                     handlers before adding new ones
    :param logger_format: the format this logger will have.
    :param propagate: propagate the message the parent logger.

    :return: A logger instance.
    :rtype: logging.Logger
    """
    if logger_format is None:
        logger_format = '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
    logger = logging.getLogger(logger_name)

    if remove_existing_handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    if not handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handlers = [handler]

    formatter = logging.Formatter(fmt=logger_format,
                                  datefmt='%H:%M:%S')
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(logger_level)
    if not propagate:
        logger.propagate = False
    return logger


def get_manager_ip():
    """
    Returns the IP address of manager inside the management network.
    """
    return os.environ[constants.MANAGER_IP_KEY]


def get_manager_file_server_blueprints_root_url():
    """
    Returns the blueprints root url in the file server.
    """
    return os.environ[constants.MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL_KEY]


def get_manager_file_server_deployments_root_url():
    """
    Returns the blueprints root url in the file server.
    """
    return os.environ[constants.MANAGER_FILE_SERVER_DEPLOYMENTS_ROOT_URL_KEY]


def get_manager_file_server_url():
    """
    Returns the manager file server base url.
    """
    return os.environ[constants.MANAGER_FILE_SERVER_URL_KEY]


def get_manager_rest_service_port():
    """
    Returns the port the manager REST service is running on.
    """
    return int(os.environ[constants.MANAGER_REST_PORT_KEY])


def get_is_bypass_maintenance():
    """
    Returns true if workflow should run in maintenance mode.
    """
    return os.environ.get(constants.BYPASS_MAINTENANCE, '').lower() == 'true'


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """
    Generate and return a random string using upper case letters and digits.
    """
    return ''.join(random.choice(chars) for _ in range(size))


def create_temp_folder():
    """
    Create a temporary folder.
    """
    path_join = os.path.join(tempfile.gettempdir(), id_generator(5))
    os.makedirs(path_join)
    return path_join


def exception_to_error_cause(exception, tb):
    error = StringIO.StringIO()
    etype = type(exception)
    traceback.print_exception(etype, exception, tb, file=error)
    return {
        'message': str(exception),
        'traceback': error.getvalue(),
        'type': etype.__name__
    }


class LocalCommandRunner(object):

    def __init__(self, logger=None, host='localhost'):

        """
        :param logger: This logger will be used for
                       printing the output and the command.
        """

        logger = logger or setup_logger('LocalCommandRunner')
        self.logger = logger
        self.host = host

    def run(self, command,
            exit_on_failure=True,
            stdout_pipe=True,
            stderr_pipe=True,
            cwd=None,
            execution_env=None):

        """
        Runs local commands.

        :param command: The command to execute.
        :param exit_on_failure: False to ignore failures.
        :param stdout_pipe: False to not pipe the standard output.
        :param stderr_pipe: False to not pipe the standard error.
        :param cwd: the working directory the command will run from.
        :param execution_env: dictionary of environment variables that will
                              be present in the command scope.

        :return: A wrapper object for all valuable info from the execution.
        :rtype: cloudify.utils.CommandExecutionResponse
        """

        self.logger.debug('[{0}] run: {1}'.format(self.host, command))
        shlex_split = _shlex_split(command)
        stdout = subprocess.PIPE if stdout_pipe else None
        stderr = subprocess.PIPE if stderr_pipe else None
        command_env = os.environ.copy()
        command_env.update(execution_env or {})
        p = subprocess.Popen(shlex_split, stdout=stdout,
                             stderr=stderr, cwd=cwd, env=command_env)
        out, err = p.communicate()
        if out:
            out = out.rstrip()
        if err:
            err = err.rstrip()

        if p.returncode != 0:
            error = CommandExecutionException(
                command=command,
                error=err,
                output=out,
                code=p.returncode)
            if exit_on_failure:
                raise error
            else:
                self.logger.error(error)

        return CommandExecutionResponse(
            command=command,
            std_out=out,
            std_err=err,
            return_code=p.returncode)


class CommandExecutionResponse(object):

    """
    Wrapper object for info returned when running commands.

    :param command: The command that was executed.
    :param std_out: The output from the execution.
    :param std_err: The error message from the execution.
    :param return_code: The return code from the execution.
    """

    def __init__(self, command, std_out, std_err, return_code):
        self.command = command
        self.std_out = std_out
        self.std_err = std_err
        self.return_code = return_code

setup_default_logger = setup_logger  # deprecated; for backwards compatibility


def _shlex_split(command):
    lex = shlex.shlex(command, posix=True)
    lex.whitespace_split = True
    lex.escape = ''
    return list(lex)


class Internal(object):

    @staticmethod
    def get_install_method(properties):
        install_agent = properties.get('install_agent')
        if install_agent is False:
            return 'none'
        elif install_agent is True:
            return 'remote'
        else:
            return properties.get('agent_config', {}).get('install_method')

    @staticmethod
    def get_broker_ssl_and_port(ssl_enabled, cert_path):
        # Input vars may be None if not set. Explicitly defining defaults.
        ssl_enabled = ssl_enabled or False
        cert_path = cert_path or ''

        if ssl_enabled:
            if not cert_path:
                raise NonRecoverableError(
                    "Broker SSL enabled but no SSL cert was provided. "
                    "If rabbitmq_ssl_enabled is True in the inputs, "
                    "rabbitmq_cert_public (and private) must be populated."
                )
            port = constants.BROKER_PORT_SSL
            ssl_options = {
                'ca_certs': cert_path,
                'cert_reqs': ssl.CERT_REQUIRED,
            }
        else:
            port = constants.BROKER_PORT_NO_SSL
            ssl_options = {}

        return port, ssl_options

    @staticmethod
    def get_broker_credentials(cloudify_agent):
        """Get broker credentials or their defaults if not set."""
        default_user = 'guest'
        default_pass = 'guest'

        try:
            broker_user = cloudify_agent.broker_user or default_user
            broker_pass = cloudify_agent.broker_pass or default_pass
        except AttributeError:
            # Handle non-agent from non-manager (e.g. for manual tests)
            broker_user = default_user
            broker_pass = default_pass

        return broker_user, broker_pass

    @staticmethod
    def plugin_prefix(package_name=None, package_version=None,
                      deployment_id=None, plugin_name=None,
                      sys_prefix_fallback=True):
        plugins_dir = os.path.join(sys.prefix, 'plugins')
        prefix = None
        if package_name and package_version:
            wagon_dir = os.path.join(plugins_dir, '{0}-{1}'.format(
                    package_name, package_version))
            if os.path.isdir(wagon_dir):
                prefix = wagon_dir
        if prefix is None and deployment_id and plugin_name:
            source_dir = os.path.join(plugins_dir, '{0}-{1}'.format(
                    deployment_id, plugin_name))
            if os.path.isdir(source_dir):
                prefix = source_dir
        if prefix is None and sys_prefix_fallback:
            prefix = sys.prefix
        return prefix


internal = Internal()
