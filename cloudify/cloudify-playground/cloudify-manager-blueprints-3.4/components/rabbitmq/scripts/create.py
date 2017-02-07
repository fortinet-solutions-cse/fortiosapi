#!/usr/bin/env python

import os
import time
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONFIG_PATH = 'components/rabbitmq/config'
RABBITMQ_SERVICE_NAME = 'rabbitmq'

ctx_properties = utils.ctx_factory.create(RABBITMQ_SERVICE_NAME)


def check_if_user_exists(username):
    if username in utils.sudo(
            ['rabbitmqctl', 'list_users'], retries=5).aggr_stdout:
        return True
    return False


def _clear_guest_permissions_if_guest_exists():
    if check_if_user_exists('guest'):
        ctx.logger.info('Disabling RabbitMQ guest user...')
        utils.sudo(['rabbitmqctl', 'clear_permissions', 'guest'], retries=5)
        utils.sudo(['rabbitmqctl', 'delete_user', 'guest'], retries=5)


def _create_user_and_set_permissions(rabbitmq_username,
                                     rabbitmq_password):
    if not check_if_user_exists(rabbitmq_username):
        ctx.logger.info('Creating new user {0}:{1} and setting '
                        'permissions...'.format(
                            rabbitmq_username, rabbitmq_password))
        utils.sudo(['rabbitmqctl', 'add_user',
                    rabbitmq_username, rabbitmq_password])
        utils.sudo(['rabbitmqctl', 'set_permissions',
                    rabbitmq_username, '.*', '.*', '.*'], retries=5)


def _set_security(rabbitmq_ssl_enabled,
                  rabbitmq_cert_private,
                  rabbitmq_cert_public):
    # Deploy certificates if both have been provided.
    # Complain loudly if one has been provided and the other hasn't.
    if rabbitmq_ssl_enabled:
        if rabbitmq_cert_private and rabbitmq_cert_public:
            utils.deploy_ssl_certificate(
                'private', '/etc/rabbitmq/rabbit-priv.pem',
                'rabbitmq', rabbitmq_cert_private)
            utils.deploy_ssl_certificate(
                'public', '/etc/rabbitmq/rabbit-pub.pem',
                'rabbitmq', rabbitmq_cert_public)
            # Configure for SSL

            utils.deploy_blueprint_resource(
                '{0}/rabbitmq.config-ssl'.format(CONFIG_PATH),
                '/etc/rabbitmq/rabbitmq.config',
                RABBITMQ_SERVICE_NAME, user_resource=True)
        else:
            ctx.abort_operation('When providing a certificate for rabbitmq, '
                                'both public and private certificates must be '
                                'supplied.')
    else:

        utils.deploy_blueprint_resource(
            '{0}/rabbitmq.config-nossl'.format(CONFIG_PATH),
            '/etc/rabbitmq/rabbitmq.config',
            RABBITMQ_SERVICE_NAME, user_resource=True)
        if rabbitmq_cert_private or rabbitmq_cert_public:
            ctx.logger.warn('Broker SSL cert supplied but SSL not enabled '
                            '(broker_ssl_enabled is False).')


def _install_rabbitmq():
    erlang_rpm_source_url = ctx_properties['erlang_rpm_source_url']
    rabbitmq_rpm_source_url = ctx_properties['rabbitmq_rpm_source_url']
    # TODO: maybe we don't need this env var
    os.putenv('RABBITMQ_FD_LIMIT',
              str(ctx_properties['rabbitmq_fd_limit']))
    rabbitmq_log_path = '/var/log/cloudify/rabbitmq'
    rabbitmq_username = ctx_properties['rabbitmq_username']
    rabbitmq_password = ctx_properties['rabbitmq_password']
    rabbitmq_cert_public = ctx_properties['rabbitmq_cert_public']
    rabbitmq_ssl_enabled = ctx_properties['rabbitmq_ssl_enabled']
    rabbitmq_cert_private = ctx_properties['rabbitmq_cert_private']

    ctx.logger.info('Installing RabbitMQ...')
    utils.set_selinux_permissive()

    utils.copy_notice(RABBITMQ_SERVICE_NAME)
    utils.mkdir(rabbitmq_log_path)

    utils.yum_install(erlang_rpm_source_url,
                      service_name=RABBITMQ_SERVICE_NAME)
    utils.yum_install(rabbitmq_rpm_source_url,
                      service_name=RABBITMQ_SERVICE_NAME)

    utils.logrotate(RABBITMQ_SERVICE_NAME)

    utils.systemd.configure(RABBITMQ_SERVICE_NAME)

    ctx.logger.info('Configuring File Descriptors Limit...')
    utils.deploy_blueprint_resource(
        '{0}/rabbitmq_ulimit.conf'.format(CONFIG_PATH),
        '/etc/security/limits.d/rabbitmq.conf',
        RABBITMQ_SERVICE_NAME)

    utils.systemd.systemctl('daemon-reload')

    utils.chown('rabbitmq', 'rabbitmq', rabbitmq_log_path)

    # rabbitmq restart exits with 143 status code that is valid in this case.
    utils.systemd.restart(RABBITMQ_SERVICE_NAME, ignore_failure=True)

    time.sleep(10)
    utils.wait_for_port(5672)

    ctx.logger.info('Enabling RabbitMQ Plugins...')
    # Occasional timing issues with rabbitmq starting have resulted in
    # failures when first trying to enable plugins
    utils.sudo(['rabbitmq-plugins', 'enable', 'rabbitmq_management'],
               retries=5)
    utils.sudo(['rabbitmq-plugins', 'enable', 'rabbitmq_tracing'], retries=5)

    _clear_guest_permissions_if_guest_exists()
    _create_user_and_set_permissions(rabbitmq_username, rabbitmq_password)
    _set_security(
        rabbitmq_ssl_enabled,
        rabbitmq_cert_private,
        rabbitmq_cert_public)

    utils.systemd.stop(RABBITMQ_SERVICE_NAME, retries=5)


def main():

    rabbitmq_endpoint_ip = ctx_properties['rabbitmq_endpoint_ip']

    if not rabbitmq_endpoint_ip:
        broker_ip = ctx.instance.host_ip
        _install_rabbitmq()
    else:
        ctx.logger.info('External RabbitMQ Endpoint provided: '
                        '{0}...'.format(rabbitmq_endpoint_ip))
        broker_ip = rabbitmq_endpoint_ip

    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = broker_ip


main()
