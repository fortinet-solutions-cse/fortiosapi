########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
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

"""
Handles 'cfy upgrade command'
"""
import os
import time
import json
import shutil
import tempfile

from cloudify_cli import ssh
from cloudify_cli import utils
from cloudify_cli import common
from cloudify_cli import exceptions
from cloudify_cli.logger import get_logger
from cloudify_cli.commands import maintenance
from cloudify_cli.bootstrap import bootstrap as bs
from cloudify_cli.bootstrap.bootstrap import load_env


MAINTENANCE_MODE_DEACTIVATED = 'deactivated'
MAINTENANCE_MODE_ACTIVATING = 'activating'

REMOTE_WORKFLOW_STATE_PATH = '/opt/cloudify/_workflow_state.json'


def upgrade(validate_only,
            skip_validations,
            blueprint_path,
            inputs,
            install_plugins,
            task_retries,
            task_retry_interval,
            task_thread_pool_size):

    logger = get_logger()
    management_ip = utils.get_management_server_ip()

    client = utils.get_rest_client(management_ip, skip_version_check=True)

    verify_and_wait_for_maintenance_mode_activation(client)

    inputs = update_inputs(inputs)
    env_name = 'manager-upgrade'
    # init local workflow execution environment
    env = common.initialize_blueprint(blueprint_path,
                                      storage=None,
                                      install_plugins=install_plugins,
                                      name=env_name,
                                      inputs=json.dumps(inputs))
    logger.info('Upgrading manager...')
    put_workflow_state_file(is_upgrade=True,
                            key_filename=inputs['ssh_key_filename'],
                            user=inputs['ssh_user'])
    if not skip_validations:
        logger.info('Executing upgrade validations...')
        env.execute(workflow='execute_operation',
                    parameters={'operation':
                                'cloudify.interfaces.validation.creation'},
                    task_retries=task_retries,
                    task_retry_interval=task_retry_interval,
                    task_thread_pool_size=task_thread_pool_size)
        logger.info('Upgrade validation completed successfully')

    if not validate_only:
        try:
            logger.info('Executing manager upgrade...')
            env.execute('install',
                        task_retries=task_retries,
                        task_retry_interval=task_retry_interval,
                        task_thread_pool_size=task_thread_pool_size)
        except Exception as e:
            msg = 'Upgrade failed! ({0})'.format(e)
            error = exceptions.CloudifyCliError(msg)
            error.possible_solutions = [
                "Rerun upgrade: `cfy upgrade`",
                "Execute rollback: `cfy rollback`"
            ]
            raise error

        manager_node = next(node for node in env.storage.get_nodes()
                            if node.id == 'manager_configuration')
        upload_resources = \
            manager_node.properties['cloudify'].get('upload_resources', {})
        dsl_resources = upload_resources.get('dsl_resources', ())
        if dsl_resources:
            fetch_timeout = upload_resources.get('parameters', {}) \
                .get('fetch_timeout', 30)
            fabric_env = bs.build_fabric_env(management_ip,
                                             inputs['ssh_user'],
                                             inputs['ssh_key_filename'])
            temp_dir = tempfile.mkdtemp()
            try:
                logger.info('Uploading dsl resources...')
                bs.upload_dsl_resources(dsl_resources,
                                        temp_dir=temp_dir,
                                        fabric_env=fabric_env,
                                        retries=task_retries,
                                        wait_interval=task_retry_interval,
                                        timeout=fetch_timeout)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        plugin_resources = upload_resources.get('plugin_resources', ())
        if plugin_resources:
            logger.warn('Plugins upload is not supported for upgrade. Plugins '
                        '{0} will not be uploaded'
                        .format(plugin_resources))

    logger.info('Upgrade complete')
    logger.info('Manager is up at {0}'.format(
        utils.get_management_server_ip()))


def update_inputs(inputs=None):
    inputs = utils.inputs_to_dict(inputs, 'inputs') or {}
    inputs.update({'private_ip': _load_private_ip(inputs)})
    inputs.update({'ssh_key_filename': _load_management_key(inputs)})
    inputs.update({'ssh_user': _load_management_user(inputs)})
    inputs.update({'public_ip': utils.get_management_server_ip()})
    return inputs


def _load_private_ip(inputs):
    try:
        return inputs['private_ip'] or load_env().outputs()['private_ip']
    except Exception:
        raise exceptions.CloudifyCliError('Private IP must be provided for '
                                          'the upgrade/rollback process')


def _load_management_key(inputs):
    try:
        key_path = inputs['ssh_key_filename'] or utils.get_management_key()
        return os.path.expanduser(key_path)
    except Exception:
        raise exceptions.CloudifyCliError('Manager key must be provided for '
                                          'the upgrade/rollback process')


def _load_management_user(inputs):
    try:
        return inputs.get('ssh_user') or utils.get_management_user()
    except Exception:
        raise exceptions.CloudifyCliError('Manager user must be provided for '
                                          'the upgrade/rollback process')


def verify_and_wait_for_maintenance_mode_activation(client):
    logger = get_logger()
    curr_status = client.maintenance_mode.status().status
    if curr_status == MAINTENANCE_MODE_DEACTIVATED:
        error = exceptions.CloudifyCliError(
            'To perform an upgrade of a manager to a newer version, '
            'the manager must be in maintenance mode')
        error.possible_solutions = [
            "Activate maintenance mode by running "
            "`cfy maintenance-mode activate`"
        ]
        raise error
    elif curr_status == MAINTENANCE_MODE_ACTIVATING:
        _wait_for_maintenance(client, logger)


def put_workflow_state_file(is_upgrade, key_filename, user):
    manager_state_file = tempfile.NamedTemporaryFile(delete=True)
    content = {'is_upgrade': is_upgrade}
    with open(manager_state_file.name, 'w') as f:
        f.write(json.dumps(content))
    ssh.put_file_in_manager(manager_state_file,
                            REMOTE_WORKFLOW_STATE_PATH,
                            key_filename=key_filename,
                            user=user)


def _wait_for_maintenance(client, logger):
    curr_status = client.maintenance_mode.status().status
    while curr_status != maintenance.MAINTENANCE_MODE_ACTIVE:
        logger.info('Waiting for maintenance mode to be activated...')
        time.sleep(maintenance.DEFAULT_TIMEOUT_INTERVAL)
        curr_status = client.maintenance_mode.status().status
