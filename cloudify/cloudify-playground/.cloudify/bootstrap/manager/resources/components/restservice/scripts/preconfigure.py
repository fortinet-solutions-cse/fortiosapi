#!/usr/bin/env python

import tempfile
import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

REST_SERVICE_NAME = 'restservice'


def preconfigure_restservice():

    rest_service_home = '/opt/manager'

    ctx.logger.info('Deploying REST Security configuration file...')
    sec_config = utils.load_manager_config_prop('security')
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        f.write(sec_config)
    utils.move(path, os.path.join(rest_service_home, 'rest-security.conf'))

    utils.systemd.configure(REST_SERVICE_NAME, render=False)


preconfigure_restservice()
