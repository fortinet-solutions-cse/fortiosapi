#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

INFLUX_SERVICE_NAME = 'influxdb'


ctx_properties = utils.ctx_factory.get(INFLUX_SERVICE_NAME)

INFLUXDB_ENDPOINT_IP = ctx_properties['influxdb_endpoint_ip']

if not INFLUXDB_ENDPOINT_IP:
    ctx.logger.info('Stopping InfluxDB Service...')
    utils.systemd.stop(INFLUX_SERVICE_NAME)
