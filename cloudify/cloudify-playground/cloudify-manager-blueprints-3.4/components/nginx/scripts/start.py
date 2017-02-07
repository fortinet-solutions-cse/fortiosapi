#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

NGINX_SERVICE_NAME = 'nginx'


def check_response(response):
    """Check if the response looks like a correct REST service response.

    We can get a 200, or a 401 in case auth is enabled. We don't expect a
    502, though, as this would mean nginx isn't correctly proxying to
    the REST service.
    """
    return response.code in {200, 401}


utils.start_service(NGINX_SERVICE_NAME, append_prefix=False)
utils.systemd.verify_alive(NGINX_SERVICE_NAME, append_prefix=False)

nginx_url = 'http://127.0.0.1/api/v2.1/blueprints'

if utils.is_upgrade or utils.is_rollback:
    headers = utils.create_maintenance_headers()
else:
    headers = utils.get_auth_headers(True)

utils.verify_service_http(NGINX_SERVICE_NAME, nginx_url, check_response,
                          headers=headers)
