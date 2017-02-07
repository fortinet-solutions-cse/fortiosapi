#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

AMQPINFLUX_SERVICE_NAME = 'amqpinflux'


ctx.logger.info('Stopping AMQP-Influx Broker Service...')
utils.systemd.stop(AMQPINFLUX_SERVICE_NAME)
