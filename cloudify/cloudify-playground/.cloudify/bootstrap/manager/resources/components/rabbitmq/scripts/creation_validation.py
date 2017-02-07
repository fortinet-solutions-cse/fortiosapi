#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


RABBITMQ_SERVICE_NAME = 'rabbitmq'

IMMUTABLE_PROPERTIES = [
    'rabbitmq_username',
    'rabbitmq_password',
    'rabbitmq_endpoint_ip',
    'rabbitmq_ssl_enabled',
    'rabbitmq_cert_public',
    'rabbitmq_cert_private'
]

if utils.is_upgrade:
    utils.validate_upgrade_directories(RABBITMQ_SERVICE_NAME)
    utils.verify_immutable_properties(RABBITMQ_SERVICE_NAME,
                                      IMMUTABLE_PROPERTIES)
