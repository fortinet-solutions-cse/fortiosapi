#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

NGINX_SERVICE_NAME = 'nginx'
ctx_properties = {'service_name': NGINX_SERVICE_NAME}


CONFIG_PATH = 'components/nginx/config'


def preconfigure_nginx():
    ssl_resources_rel_path = 'resources/ssl'
    ssl_certs_root = '/root/cloudify'

    # this is used by nginx's default.conf to select the relevant configuration
    rest_protocol = ctx.target.instance.runtime_properties['rest_protocol']

    # TODO: NEED TO IMPLEMENT THIS IN CTX UTILS
    ctx.source.instance.runtime_properties['rest_protocol'] = rest_protocol
    if rest_protocol == 'https':
        ctx.logger.info('Copying SSL Certs...')
        utils.mkdir(ssl_certs_root)
        utils.deploy_blueprint_resource(
            '{0}/server.crt'.format(ssl_resources_rel_path),
            '{0}/server.crt'.format(ssl_certs_root),
            NGINX_SERVICE_NAME,
            user_resource=True,
            load_ctx=False)
        utils.deploy_blueprint_resource(
            '{0}/server.key'.format(ssl_resources_rel_path),
            '{0}/server.key'.format(ssl_certs_root),
            NGINX_SERVICE_NAME,
            user_resource=True,
            load_ctx=False)

    ctx.logger.info('Deploying Nginx configuration files...')
    utils.deploy_blueprint_resource(
        '{0}/{1}-rest-server.cloudify'.format(CONFIG_PATH, rest_protocol),
        '/etc/nginx/conf.d/{0}-rest-server.cloudify'.format(rest_protocol),
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/nginx.conf'.format(CONFIG_PATH),
        '/etc/nginx/nginx.conf',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/default.conf'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/default.conf',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/rest-location.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/rest-location.cloudify',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/fileserver-location.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/fileserver-location.cloudify',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/ui-locations.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/ui-locations.cloudify',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/logs-conf.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/logs-conf.cloudify',
        NGINX_SERVICE_NAME, load_ctx=False)

    utils.systemd.enable(NGINX_SERVICE_NAME,
                         append_prefix=False)


preconfigure_nginx()
