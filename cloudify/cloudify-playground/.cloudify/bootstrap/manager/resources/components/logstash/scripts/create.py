#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONFIG_PATH = 'components/logstash/config'
LOGSTASH_SERVICE_NAME = 'logstash'

ctx_properties = utils.ctx_factory.create(LOGSTASH_SERVICE_NAME)


def install_logstash():

    logstash_unit_override = '/etc/systemd/system/logstash.service.d'

    logstash_source_url = ctx_properties['logstash_rpm_source_url']

    rabbitmq_username = ctx_properties['rabbitmq_username']
    rabbitmq_password = ctx_properties['rabbitmq_password']

    logstash_log_path = '/var/log/cloudify/logstash'
    logstash_conf_path = '/etc/logstash/conf.d'

    # injected as an input to the script
    ctx.instance.runtime_properties['es_endpoint_ip'] = \
        os.environ['ES_ENDPOINT_IP']
    elasticsearch_props = utils.ctx_factory.get('elasticsearch')
    ctx.instance.runtime_properties['es_endpoint_port'] = \
        elasticsearch_props['es_endpoint_port']

    rabbit_props = utils.ctx_factory.get('rabbitmq')
    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = \
        utils.get_rabbitmq_endpoint_ip(
            rabbit_props.get('rabbitmq_endpoint_ip'))
    ctx.instance.runtime_properties['rabbitmq_username'] = \
        rabbit_props['rabbitmq_username']
    ctx.instance.runtime_properties['rabbitmq_password'] = \
        rabbit_props['rabbitmq_password']

    # Confirm username and password have been supplied for broker before
    # continuing.
    # Components other than logstash and riemann have this handled in code.
    # Note that these are not directly used in this script, but are used by the
    # deployed resources, hence the check here.
    if not rabbitmq_username or not rabbitmq_password:
        ctx.abort_operation(
            'Both rabbitmq_username and rabbitmq_password must be supplied '
            'and at least 1 character long in the manager blueprint inputs.')

    ctx.logger.info('Installing Logstash...')
    utils.set_selinux_permissive()
    utils.copy_notice(LOGSTASH_SERVICE_NAME)

    utils.yum_install(logstash_source_url, service_name=LOGSTASH_SERVICE_NAME)

    utils.mkdir(logstash_log_path)
    utils.chown('logstash', 'logstash', logstash_log_path)

    ctx.logger.info('Creating systemd unit override...')
    utils.mkdir(logstash_unit_override)
    utils.deploy_blueprint_resource(
        '{0}/restart.conf'.format(CONFIG_PATH),
        '{0}/restart.conf'.format(logstash_unit_override),
        LOGSTASH_SERVICE_NAME)
    ctx.logger.info('Deploying Logstash conf...')
    utils.deploy_blueprint_resource(
        '{0}/logstash.conf'.format(CONFIG_PATH),
        '{0}/logstash.conf'.format(logstash_conf_path),
        LOGSTASH_SERVICE_NAME)

    # Due to a bug in the handling of configuration files,
    # configuration files with the same name cannot be deployed.
    # Since the logrotate config file is called `logstash`,
    # we change the name of the logstash env vars config file
    # from logstash to cloudify-logstash to be consistent with
    # other service env var files.
    init_file = '/etc/init.d/logstash'
    utils.replace_in_file(
        'sysconfig/\$name',
        'sysconfig/cloudify-$name',
        init_file)
    utils.chmod('755', init_file)
    utils.chown('root', 'root', init_file)

    ctx.logger.info('Deploying Logstash sysconfig...')
    utils.deploy_blueprint_resource(
        '{0}/cloudify-logstash'.format(CONFIG_PATH),
        '/etc/sysconfig/cloudify-logstash',
        LOGSTASH_SERVICE_NAME)

    utils.logrotate(LOGSTASH_SERVICE_NAME)
    utils.sudo(['/sbin/chkconfig', 'logstash', 'on'])
    utils.clean_var_log_dir(LOGSTASH_SERVICE_NAME)


install_logstash()
