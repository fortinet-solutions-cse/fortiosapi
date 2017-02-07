#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

RABBITMQ_SERVICE_NAME = 'rabbitmq'


ctx.logger.info("Stopping RabbitMQ Service...")
utils.systemd.stop(RABBITMQ_SERVICE_NAME, ignore_failure=True)
