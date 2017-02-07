#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

IMMUTABLE_PROPERTIES = [
    'security',
    'ssh_user'
]

if utils.is_upgrade:
    utils.verify_immutable_properties('manager-config', IMMUTABLE_PROPERTIES)
