#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

MGMT_WORKER_SERVICE_NAME = 'mgmtworker'


ctx.logger.info('Stopping Management Worker Service...')
utils.systemd.stop(MGMT_WORKER_SERVICE_NAME)
