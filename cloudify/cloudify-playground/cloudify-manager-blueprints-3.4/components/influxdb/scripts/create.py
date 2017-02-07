#!/usr/bin/env python

import time
import json
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

CONFIG_PATH = "components/influxdb/config"
INFLUX_SERVICE_NAME = 'influxdb'

ctx_properties = utils.ctx_factory.create(INFLUX_SERVICE_NAME)


def _configure_influxdb(host, port):
    db_user = "root"
    db_pass = "root"
    db_name = "cloudify"

    ctx.logger.info('Creating InfluxDB Database...')

    # the below request is equivalent to running:
    # curl -S -s "http://localhost:8086/db?u=root&p=root" '-d "{\"name\": \"cloudify\"}"  # NOQA
    import urllib
    import urllib2

    endpoint = 'http://{0}:{1}/db'.format(host, port)
    params = urllib.urlencode(dict(u=db_user, p=db_pass))
    data = {'name': db_name}
    url = endpoint + '?' + params

    # check if db already exists
    db_list = eval(urllib2.urlopen(urllib2.Request(url)).read())
    try:
        assert not any(d.get('name') == db_name for d in db_list)
    except AssertionError:
        ctx.logger.info('Database {0} already exists!'.format(db_name))
        return

    ctx.logger.info('Request is: {0} \'{1}\''.format(url, data))

    try:
        urllib2.urlopen(urllib2.Request(url, json.dumps(data)))
    except Exception as ex:
        msg = 'Failed to create: {0} ({1}).'.format(db_name, ex)
        ctx.abort_operation(msg)

    # verify db created
    ctx.logger.info('Verifying database create successfully...')
    db_list = eval(urllib2.urlopen(urllib2.Request(url)).read())
    try:
        assert any(d.get('name') == db_name for d in db_list)
    except AssertionError:
        msg = 'Verification failed!'
        ctx.abort_operation(msg)
    ctx.logger.info('Databased {0} created successfully.'.format(db_name))


def _install_influxdb():

    influxdb_source_url = ctx_properties['influxdb_rpm_source_url']

    influxdb_user = 'influxdb'
    influxdb_group = 'influxdb'
    influxdb_home = '/opt/influxdb'
    influxdb_log_path = '/var/log/cloudify/influxdb'

    ctx.logger.info('Installing InfluxDB...')
    utils.set_selinux_permissive()

    utils.copy_notice(INFLUX_SERVICE_NAME)
    utils.mkdir(influxdb_home)
    utils.mkdir(influxdb_log_path)

    utils.yum_install(influxdb_source_url, service_name=INFLUX_SERVICE_NAME)
    utils.sudo(['rm', '-rf', '/etc/init.d/influxdb'])

    ctx.logger.info('Deploying InfluxDB config.toml...')
    utils.deploy_blueprint_resource(
        '{0}/config.toml'.format(CONFIG_PATH),
        '{0}/shared/config.toml'.format(influxdb_home),
        INFLUX_SERVICE_NAME)

    ctx.logger.info('Fixing user permissions...')
    utils.chown(influxdb_user, influxdb_group, influxdb_home)
    utils.chown(influxdb_user, influxdb_group, influxdb_log_path)

    utils.systemd.configure(INFLUX_SERVICE_NAME)
    # Provided with InfluxDB's package. Will be removed if it exists.
    utils.remove('/etc/init.d/influxdb')
    utils.logrotate(INFLUX_SERVICE_NAME)


def main():

    influxdb_endpoint_ip = ctx_properties['influxdb_endpoint_ip']
    # currently, cannot be changed due to webui not allowing to configure it.
    influxdb_endpoint_port = 8086

    if influxdb_endpoint_ip:
        ctx.logger.info('External InfluxDB Endpoint IP provided: {0}'.format(
            influxdb_endpoint_ip))
        time.sleep(5)
        utils.wait_for_port(influxdb_endpoint_port, influxdb_endpoint_ip)
        _configure_influxdb(influxdb_endpoint_ip, influxdb_endpoint_port)
    else:
        influxdb_endpoint_ip = ctx.instance.host_ip
        _install_influxdb()

        utils.systemd.restart(INFLUX_SERVICE_NAME)

        utils.wait_for_port(influxdb_endpoint_port, influxdb_endpoint_ip)
        _configure_influxdb(influxdb_endpoint_ip, influxdb_endpoint_port)

        utils.systemd.stop(INFLUX_SERVICE_NAME)

    ctx.instance.runtime_properties['influxdb_endpoint_ip'] = \
        influxdb_endpoint_ip


main()
