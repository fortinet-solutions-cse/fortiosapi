#!/bin/python

import fabric.api

from cloudify import ctx


def upload_keypair(local_key_path):
    ctx.logger.info('Uploading key {0}...'.format(local_key_path))
    manager_remote_key_path = '/tmp/mng-key.pem'
    fabric.api.put(local_key_path,
                   manager_remote_key_path,
                   use_sudo=True)

    ctx.instance.runtime_properties['manager_remote_key_path'] = \
        manager_remote_key_path
