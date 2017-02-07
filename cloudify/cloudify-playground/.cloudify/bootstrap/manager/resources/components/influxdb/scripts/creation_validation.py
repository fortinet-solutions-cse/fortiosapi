#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

INFLUX_SERVICE_NAME = 'influxdb'

if utils.is_upgrade:
    utils.validate_upgrade_directories(INFLUX_SERVICE_NAME)
    utils.systemd.verify_alive(INFLUX_SERVICE_NAME)
