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
INFLUXDB_ENDPOINT_PORT = 8086


def check_influxdb_response(response):
    """Check if the response from influxdb is correct.

    InfluxDB normally responds with a 404 on GET to /, but also allow other
    non-server-error response codes to allow for that behaviour to change.
    """
    return response.code < 500


if not INFLUXDB_ENDPOINT_IP:
    ctx.logger.info('Starting InfluxDB Service...')
    utils.start_service(INFLUX_SERVICE_NAME)

    INFLUXDB_ENDPOINT_IP = '127.0.0.1'

    utils.systemd.verify_alive(INFLUX_SERVICE_NAME)

influxdb_url = 'http://{0}:{1}'.format(
    INFLUXDB_ENDPOINT_IP, INFLUXDB_ENDPOINT_PORT)


utils.verify_service_http(INFLUX_SERVICE_NAME, influxdb_url,
                          check_influxdb_response)
