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

CLOUDIFY_WD_SETTINGS_FILE_NAME = 'context'
CLOUDIFY_WD_SETTINGS_DIRECTORY_NAME = '.cloudify'
CONFIG_FILE_NAME = 'cloudify-config.yaml'
DEFAULTS_CONFIG_FILE_NAME = 'cloudify-config.defaults.yaml'
DEFAULT_BLUEPRINT_FILE_NAME = 'blueprint.yaml'
DEFAULT_BLUEPRINT_PATH = 'blueprint.yaml'
DEFAULT_INPUTS_PATH_FOR_INSTALL_COMMAND = 'inputs.yaml'
DEFAULT_PARAMETERS = None
DEFAULT_TIMEOUT = 900
DEFAULT_TASK_THREAD_POOL_SIZE = 1
DEFAULT_INSTALL_WORKFLOW = 'install'
DEFAULT_UNINSTALL_WORKFLOW = 'uninstall'

AGENT_MIN_WORKERS = 2
AGENT_MAX_WORKERS = 5
AGENT_KEY_PATH = '~/.ssh/cloudify-agents-kp.pem'
AGENT_REMOTE_KEY_PATH = '~/.ssh/agent_key.pem'
REMOTE_EXECUTION_PORT = 22

WORKFLOW_TASK_RETRIES = -1
WORKFLOW_TASK_RETRY_INTERVAL = 30

POLICY_ENGINE_START_TIMEOUT = 30

DEFAULT_REST_PORT = 80
SECURED_REST_PORT = 443
DEFAULT_PROTOCOL = 'http'
SECURED_PROTOCOL = 'https'

CLOUDIFY_PACKAGES_PATH = '/cloudify'
CLOUDIFY_COMPONENTS_PACKAGE_PATH = '/cloudify-components'
CLOUDIFY_CORE_PACKAGE_PATH = '/cloudify-core'
CLOUDIFY_UI_PACKAGE_PATH = '/cloudify-ui'
CLOUDIFY_AGENT_PACKAGE_PATH = '/cloudify-agents'

CLOUDIFY_REST_CLIENT_LOGGER_NAME = 'cloudify.rest_client.http'

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'cloudify_agent.operations',
    'cloudify_agent.installer.operations',

    # maintained for backward compatibily with < 3.3 blueprints
    'worker_installer.tasks',
    'plugin_installer.tasks',
    'windows_agent_installer.tasks',
    'windows_plugin_installer.tasks',
)

CLOUDIFY_AUTHENTICATION_HEADER = 'Authorization'
CLOUDIFY_USERNAME_ENV = 'CLOUDIFY_USERNAME'
CLOUDIFY_PASSWORD_ENV = 'CLOUDIFY_PASSWORD'

CLOUDIFY_SSL_CERT = 'CLOUDIFY_SSL_CERT'
CLOUDIFY_SSL_TRUST_ALL = 'CLOUDIFY_SSL_TRUST_ALL'

SSL_ENABLED_PROPERTY_NAME = 'enabled'
SSL_CERTIFICATE_PATH_PROPERTY_NAME = 'certificate_path'
SSL_PRIVATE_KEY_PROPERTY_NAME = 'private_key_path'

BASIC_AUTH_PREFIX = 'Basic'

API_VERSION = 'v2'

HELP_TEXT_COLUMN_BUFFER = 5
