#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

WEBUI_SERVICE_NAME = 'webui'


CONFIG_PATH = 'components/webui/config'

ctx_properties = utils.ctx_factory.create(WEBUI_SERVICE_NAME)


def install_webui():

    nodejs_source_url = ctx_properties['nodejs_tar_source_url']
    webui_source_url = ctx_properties['webui_tar_source_url']
    grafana_source_url = ctx_properties['grafana_tar_source_url']

    # injected as an input to the script
    ctx.instance.runtime_properties['influxdb_endpoint_ip'] = \
        os.environ.get('INFLUXDB_ENDPOINT_IP')

    nodejs_home = '/opt/nodejs'
    webui_home = '/opt/cloudify-ui'
    webui_log_path = '/var/log/cloudify/webui'
    grafana_home = '{0}/grafana'.format(webui_home)

    webui_user = 'webui'
    webui_group = 'webui'

    ctx.logger.info('Installing Cloudify\'s WebUI...')
    utils.set_selinux_permissive()

    utils.copy_notice(WEBUI_SERVICE_NAME)

    utils.mkdir(nodejs_home)
    utils.mkdir(webui_home)
    utils.mkdir('{0}/backend'.format(webui_home))
    utils.mkdir(webui_log_path)
    utils.mkdir(grafana_home)

    utils.create_service_user(webui_user, webui_home)

    ctx.logger.info('Installing NodeJS...')
    nodejs = utils.download_cloudify_resource(nodejs_source_url,
                                              WEBUI_SERVICE_NAME)
    utils.untar(nodejs, nodejs_home)

    ctx.logger.info('Installing Cloudify\'s WebUI...')
    webui = utils.download_cloudify_resource(webui_source_url,
                                             WEBUI_SERVICE_NAME)
    utils.untar(webui, webui_home)

    ctx.logger.info('Installing Grafana...')
    grafana = utils.download_cloudify_resource(grafana_source_url,
                                               WEBUI_SERVICE_NAME)
    utils.untar(grafana, grafana_home)

    ctx.logger.info('Deploying WebUI Configuration...')
    utils.deploy_blueprint_resource(
        '{0}/gsPresets.json'.format(CONFIG_PATH),
        '{0}/backend/gsPresets.json'.format(webui_home),
        WEBUI_SERVICE_NAME)
    ctx.logger.info('Deploying Grafana Configuration...')
    utils.deploy_blueprint_resource(
        '{0}/grafana_config.js'.format(CONFIG_PATH),
        '{0}/config.js'.format(grafana_home),
        WEBUI_SERVICE_NAME)

    ctx.logger.info('Fixing permissions...')
    utils.chown(webui_user, webui_group, webui_home)
    utils.chown(webui_user, webui_group, nodejs_home)
    utils.chown(webui_user, webui_group, webui_log_path)

    utils.logrotate(WEBUI_SERVICE_NAME)
    utils.systemd.configure(WEBUI_SERVICE_NAME)


def main():
    install_webui()


main()
