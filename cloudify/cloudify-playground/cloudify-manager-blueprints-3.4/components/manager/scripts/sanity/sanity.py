#!/usr/bin/env python

import os
import json
import urllib
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
        join('components', 'utils.py'),
        join(dirname(__file__), 'utils.py'))
import utils  # NOQA

REST_VERSION = 'v2.1'
BLUEPRINT_ID = 'sanity_bp'
DEPLOYMENT_ID = 'sanity_deployment'
SANITY_SERVICE_NAME = 'sanity'

manager_ip = os.environ.get('manager_ip')
manager_user = os.environ.get('manager_user')
manager_remote_key_path = \
    ctx.instance.runtime_properties['manager_remote_key_path']
rest_protocol = ctx.instance.runtime_properties['rest_protocol']
rest_port = ctx.instance.runtime_properties['rest_port']
ctx_properties = utils.ctx_factory.create(SANITY_SERVICE_NAME)


def _prepare_sanity_app():
    sanity_app_source_url = ctx_properties['sanity_app_source_url']
    app_tar = utils.download_cloudify_resource(
              url=sanity_app_source_url,
              service_name=SANITY_SERVICE_NAME)

    _upload_app_blueprint(app_tar)
    _deploy_app()


def _upload_app_blueprint(app_tar):
    if _is_sanity_blueprint_exist(should_fail=True):
        return

    with open(app_tar, 'rb') as f:
        app_data = f.read()
    length = os.path.getsize(app_tar)

    headers = utils.create_maintenance_headers()
    headers['Content-Length'] = length
    headers['Content-Type'] = 'application/octet-stream'
    params = urllib.urlencode(
            dict(application_file_name='no-monitoring-'
                                       'singlehost-blueprint.yaml'))

    endpoint = '{0}/blueprints/{1}'.format(_get_url_prefix(), BLUEPRINT_ID)
    url = endpoint + '?' + params
    utils.http_request(url,
                       data=app_data,
                       headers=headers)


def _deploy_app():
    if _is_sanity_dep_exist(should_fail=True):
        return

    dep_inputs = {'server_ip': manager_ip,
                  'agent_user': manager_user,
                  'agent_private_key_path': manager_remote_key_path}
    data = {
        'blueprint_id': BLUEPRINT_ID,
        'inputs': dep_inputs
    }
    headers = utils.create_maintenance_headers()
    headers.update({'content-type': 'application/json'})

    utils.http_request(
            '{0}/deployments/{1}'.format(_get_url_prefix(), DEPLOYMENT_ID),
            data=json.dumps(data),
            headers=headers)

    # Waiting for create deployment env to end
    utils.repetitive(
        utils.wait_for_workflow,
        deployment_id=DEPLOYMENT_ID,
        workflow_id='create_deployment_environment',
        url_prefix=_get_url_prefix(),
        timeout_msg='Timed out while waiting for '
                    'deployment {0} to be created'.format(DEPLOYMENT_ID))


def _install_sanity_app():
    data = {
        'deployment_id': DEPLOYMENT_ID,
        'workflow_id': 'install'
    }
    headers = utils.create_maintenance_headers()
    headers.update({'content-type': 'application/json'})

    resp = utils.http_request(
            '{0}/executions'.format(_get_url_prefix()),
            method='POST',
            data=json.dumps(data),
            headers=headers)

    # Waiting for installation to complete
    utils.repetitive(
        utils.wait_for_workflow,
        timeout=5*60,
        interval=30,
        deployment_id=DEPLOYMENT_ID,
        workflow_id='install',
        url_prefix=_get_url_prefix(),
        timeout_msg='Timed out while waiting for '
                    'deployment {0} to install'.format(DEPLOYMENT_ID))

    resp_content = resp.readlines()
    json_resp = json.loads(resp_content[0])
    return json_resp['id']


def _assert_logs_and_events(execution_id):
    headers = utils.create_maintenance_headers()
    params = urllib.urlencode(
            dict(execution_id=execution_id,
                 type='cloudify_log'))

    endpoint = '{0}/events'.format(_get_url_prefix())
    url = endpoint + '?' + params
    resp = utils.http_request(url, method='GET', headers=headers, timeout=30)
    if not resp:
        ctx.abort_operation("Can't connect to elasticsearch")
    if resp.code != 200:
        ctx.abort_operation('Failed to retrieve logs/events')

    resp_content = resp.readlines()
    json_resp = json.loads(resp_content[0])

    if 'items' not in json_resp or not json_resp['items']:
        ctx.abort_operation('No logs/events received')


def _assert_webserver_running():
    resp = utils.http_request(
        'http://localhost:8080',
        method='GET',
        timeout=10)

    if not resp:
        ctx.abort_operation("Can't connect to webserver")
    if resp.code != 200:
        ctx.abort_operation('Sanity app webserver failed to start')


def _cleanup_sanity():
    _uninstall_sanity_app()
    _delete_sanity_deployment()
    _delete_sanity_blueprint()
    _delete_key_file()


def _uninstall_sanity_app():
    if not _is_sanity_dep_exist():
        return

    data = {
        'deployment_id': DEPLOYMENT_ID,
        'workflow_id': 'uninstall'
    }
    headers = utils.create_maintenance_headers()
    headers.update({'content-type': 'application/json'})

    utils.http_request(
        '{0}/executions'.format(_get_url_prefix()),
        method='POST',
        data=json.dumps(data),
        headers=headers)

    # Waiting for installation to complete
    utils.repetitive(
        utils.wait_for_workflow,
        timeout=5*60,
        interval=30,
        deployment_id=DEPLOYMENT_ID,
        workflow_id='uninstall',
        url_prefix=_get_url_prefix(),
        timeout_msg='Timed out while waiting for '
                    'deployment {0} to uninstall.'.format(DEPLOYMENT_ID))


def _delete_sanity_deployment():
    if not _is_sanity_dep_exist():
        return
    headers = utils.create_maintenance_headers()

    resp = utils.http_request(
        '{0}/deployments/{1}'.format(_get_url_prefix(), DEPLOYMENT_ID),
        method='DELETE',
        headers=headers)

    if resp.code != 200:
        ctx.abort_operation('Failed deleting '
                            'deployment {0}: {1}'.format(DEPLOYMENT_ID,
                                                         resp.reason))


def _delete_sanity_blueprint():
    if not _is_sanity_blueprint_exist():
        return
    headers = utils.create_maintenance_headers()
    resp = utils.http_request(
        '{0}/blueprints/{1}'.format(_get_url_prefix(), BLUEPRINT_ID),
        method='DELETE',
        headers=headers)

    if resp.code != 200:
        ctx.abort_operation('Failed deleting '
                            'deployment {0}: {1}'.format(BLUEPRINT_ID,
                                                         resp.reason))


def _delete_key_file():
    if os.path.isfile(manager_remote_key_path):
        os.remove(manager_remote_key_path)


def _is_sanity_dep_exist(should_fail=False):
    headers = utils.create_maintenance_headers()
    res = utils.http_request(
        '{0}/deployments/{1}'.format(_get_url_prefix(), DEPLOYMENT_ID),
        method='GET',
        headers=headers,
        should_fail=should_fail)
    if not res:
        return False
    return res.code == 200


def _is_sanity_blueprint_exist(should_fail=False):
    headers = utils.create_maintenance_headers()
    res = utils.http_request(
            '{0}/blueprints/{1}'.format(_get_url_prefix(), BLUEPRINT_ID),
            method='GET',
            headers=headers,
            should_fail=should_fail)
    if not res:
        return False
    return res.code == 200


def _get_url_prefix():
    return '{0}://{1}:{2}/api/{3}'.format(
            rest_protocol,
            manager_ip,
            rest_port,
            REST_VERSION)


def perform_sanity():
    ctx.logger.info('Starting Manager sanity check...')
    _prepare_sanity_app()
    ctx.logger.info('Installing sanity app...')
    exec_id = _install_sanity_app()
    ctx.logger.info('Sanity app installed. Performing sanity test...')
    _assert_webserver_running()
    _assert_logs_and_events(exec_id)
    ctx.logger.info('Manager sanity check successful, '
                    'cleaning up sanity resources.')
    _cleanup_sanity()

# the 'run_sanity' parameter is injected explicitly from the cli as an
# operation parameter with 'true' as its value.
# This is done to prevent the sanity test from running before the
# provider context is available.
if os.environ.get('run_sanity') == 'true' or \
        utils.is_upgrade or \
        utils.is_rollback:
    perform_sanity()

if utils.is_upgrade or utils.is_rollback:
    utils.restore_upgrade_snapshot()

if utils.is_upgrade:
    utils.set_upgrade_success_in_upgrade_meta()
