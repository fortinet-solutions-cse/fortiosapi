#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py')
)
import utils  # NOQA

NODE_NAME = 'manager-config'

ctx_properties = utils.ctx_factory.create(NODE_NAME)


def _disable_requiretty():
    script_dest = '/tmp/configure_manager.sh'
    utils.deploy_blueprint_resource('components/manager/scripts'
                                    '/configure_manager.sh',
                                    script_dest,
                                    NODE_NAME)

    utils.sudo('chmod +x {0}'.format(script_dest))
    utils.sudo(script_dest)


def _set_ports():

    security = ctx_properties['security']
    sec_enabled = security['enabled']
    ssl_enabled = security['ssl']['enabled']

    if sec_enabled and ssl_enabled:
        ctx.logger.info('SSL is enabled, setting rest port to 443...')
        ctx.instance.runtime_properties['rest_port'] = 443
        ctx.instance.runtime_properties['rest_protocol'] = 'https'
    else:
        ctx.instance.runtime_properties['rest_port'] = 80
        ctx.instance.runtime_properties['rest_protocol'] = 'http'


def main():
    if utils.is_upgrade:
        utils.create_upgrade_snapshot()
    _disable_requiretty()
    _set_ports()

main()
