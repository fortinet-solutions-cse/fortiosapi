#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONFIG_PATH = "components/mgmtworker/config"
MGMT_WORKER_SERVICE_NAME = 'mgmtworker'

ctx_properties = utils.ctx_factory.create(MGMT_WORKER_SERVICE_NAME)


def _install_optional(mgmtworker_venv):

    rest_props = utils.ctx_factory.get('restservice')
    rest_client_source_url = \
        rest_props['rest_client_module_source_url']
    plugins_common_source_url = \
        rest_props['plugins_common_module_source_url']
    script_plugin_source_url = \
        rest_props['script_plugin_module_source_url']
    rest_service_source_url = \
        rest_props['rest_service_module_source_url']
    agent_source_url = \
        rest_props['agent_module_source_url']

    # this allows to upgrade modules if necessary.
    ctx.logger.info('Installing Optional Packages if supplied...')
    if rest_client_source_url:
        utils.install_python_package(rest_client_source_url, mgmtworker_venv)
    if plugins_common_source_url:
        utils.install_python_package(
            plugins_common_source_url, mgmtworker_venv)
    if script_plugin_source_url:
        utils.install_python_package(script_plugin_source_url, mgmtworker_venv)
    if agent_source_url:
        utils.install_python_package(agent_source_url, mgmtworker_venv)

    if rest_service_source_url:
        ctx.logger.info('Downloading cloudify-manager Repository...')
        manager_repo = \
            utils.download_cloudify_resource(rest_service_source_url,
                                             MGMT_WORKER_SERVICE_NAME)
        ctx.logger.info('Extracting Manager Repository...')
        utils.untar(manager_repo)

        ctx.logger.info('Installing Management Worker Plugins...')
        # shouldn't we extract the riemann-controller and workflows modules to
        # their own repos?
        utils.install_python_package(
            '/tmp/plugins/riemann-controller', mgmtworker_venv)
        utils.install_python_package('/tmp/workflows', mgmtworker_venv)


def install_mgmtworker():

    management_worker_rpm_source_url = \
        ctx_properties['management_worker_rpm_source_url']

    # these must all be exported as part of the start operation.
    # they will not persist, so we should use the new agent
    # don't forget to change all localhosts to the relevant ips
    mgmtworker_home = '/opt/mgmtworker'
    mgmtworker_venv = '{0}/env'.format(mgmtworker_home)
    celery_work_dir = '{0}/work'.format(mgmtworker_home)
    celery_log_dir = "/var/log/cloudify/mgmtworker"

    broker_port_ssl = '5671'
    broker_port_no_ssl = '5672'
    rabbit_props = utils.ctx_factory.get('rabbitmq')
    rabbitmq_ssl_enabled = rabbit_props['rabbitmq_ssl_enabled']
    ctx.logger.info("rabbitmq_ssl_enabled: {0}".format(rabbitmq_ssl_enabled))
    rabbitmq_cert_public = rabbit_props['rabbitmq_cert_public']

    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = \
        utils.get_rabbitmq_endpoint_ip(
                rabbit_props.get('rabbitmq_endpoint_ip'))

    # Fix possible injections in json of rabbit credentials
    # See json.org for string spec
    for key in ['rabbitmq_username', 'rabbitmq_password']:
        # We will not escape newlines or other control characters,
        # we will accept them breaking
        # things noisily, e.g. on newlines and backspaces.
        # TODO: add:
        # sed 's/"/\\"/' | sed 's/\\/\\\\/' | sed s-/-\\/- | sed 's/\t/\\t/'
        ctx.instance.runtime_properties[key] = ctx_properties[key]

    # Make the ssl enabled flag work with json (boolean in lower case)
    # TODO: check if still needed:
    # broker_ssl_enabled = "$(echo ${rabbitmq_ssl_enabled} | tr '[:upper:]' '[:lower:]')"  # NOQA
    ctx.instance.runtime_properties['rabbitmq_ssl_enabled'] = \
        rabbitmq_ssl_enabled

    ctx.logger.info('Installing Management Worker...')
    utils.set_selinux_permissive()

    utils.copy_notice(MGMT_WORKER_SERVICE_NAME)
    utils.mkdir(mgmtworker_home)
    utils.mkdir('{0}/config'.format(mgmtworker_home))
    utils.mkdir(celery_log_dir)
    utils.mkdir(celery_work_dir)

    # this create the mgmtworker_venv and installs the relevant
    # modules into it.
    utils.yum_install(management_worker_rpm_source_url,
                      service_name=MGMT_WORKER_SERVICE_NAME)
    _install_optional(mgmtworker_venv)

    # Add certificate and select port, as applicable
    if rabbitmq_ssl_enabled:
        broker_cert_path = '{0}/amqp_pub.pem'.format(mgmtworker_home)
        utils.deploy_ssl_certificate(
            'public', broker_cert_path, 'root', rabbitmq_cert_public)
        ctx.instance.runtime_properties['broker_cert_path'] = broker_cert_path
        # Use SSL port
        ctx.instance.runtime_properties['broker_port'] = broker_port_ssl
    else:
        # No SSL, don't use SSL port
        ctx.instance.runtime_properties['broker_port'] = broker_port_no_ssl
        if rabbitmq_cert_public is not None:
            ctx.logger.warn('Broker SSL cert supplied but SSL not enabled '
                            '(broker_ssl_enabled is False).')

    ctx.logger.info("broker_port: {0}".format(
        ctx.instance.runtime_properties['broker_port']))
    ctx.logger.info('Configuring Management worker...')
    # Deploy the broker configuration
    # TODO: This will break interestingly if mgmtworker_venv is empty.
    # Some sort of check for that would be sensible.
    # To sandy: I don't quite understand this check...
    # there is no else here..
    # for python_path in ${mgmtworker_venv}/lib/python*; do
    if os.path.isfile(os.path.join(mgmtworker_venv, 'bin/python')):
        broker_conf_path = os.path.join(celery_work_dir, 'broker_config.json')
        utils.deploy_blueprint_resource(
            '{0}/broker_config.json'.format(CONFIG_PATH), broker_conf_path,
            MGMT_WORKER_SERVICE_NAME)
        # The config contains credentials, do not let the world read it
        utils.sudo(['chmod', '440', broker_conf_path])
    utils.systemd.configure(MGMT_WORKER_SERVICE_NAME)
    utils.logrotate(MGMT_WORKER_SERVICE_NAME)


install_mgmtworker()
