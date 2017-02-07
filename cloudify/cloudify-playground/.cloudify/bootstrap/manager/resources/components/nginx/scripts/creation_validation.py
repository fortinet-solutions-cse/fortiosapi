#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


NGINX_SERVICE_NAME = 'nginx'

if utils.is_upgrade:
    utils.validate_upgrade_directories(NGINX_SERVICE_NAME)
    utils.systemd.verify_alive(NGINX_SERVICE_NAME, append_prefix=False)
