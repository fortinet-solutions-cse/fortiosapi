#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

MGMT_WORKER_SERVICE_NAME = 'mgmtworker'

if utils.is_upgrade:
    utils.validate_upgrade_directories(MGMT_WORKER_SERVICE_NAME)
    utils.systemd.verify_alive(MGMT_WORKER_SERVICE_NAME)
