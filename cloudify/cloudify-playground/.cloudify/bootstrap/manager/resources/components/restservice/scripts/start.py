#!/usr/bin/env python

import json
import urllib2
import urlparse
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

REST_SERVICE_NAME = 'restservice'
REST_SERVICE_HOME = '/opt/manager'


def verify_restservice(url):
    """To verify that the REST service is working, GET the blueprints list.

    There's nothing special about the blueprints endpoint, it's simply one
    that also requires the storage backend to be up, so if it works, there's
    a good chance everything is configured correctly.
    """
    blueprints_url = urlparse.urljoin(url, 'api/v2.1/blueprints')

    headers = utils.get_auth_headers(True)

    if utils.is_upgrade or utils.is_rollback:
        # if we're doing an upgrade, we're in maintenance mode - this request
        # is safe to perform in maintenance mode, so let's bypass the check
        headers = utils.create_maintenance_headers()
    else:
        headers = utils.get_auth_headers(True)

    req = urllib2.Request(blueprints_url, headers=headers)

    try:
        response = urllib2.urlopen(req)
    except urllib2.URLError as e:
        ctx.abort_operation('REST service returned an invalid response: {0}'
                            .format(e))
    if response.code == 401:
        ctx.abort_operation('Could not connect to the REST service: '
                            '401 unauthorized. Possible access control '
                            'misconfiguration')
    if response.code != 200:
        ctx.abort_operation('REST service returned an unexpected response: {0}'
                            .format(response.code))

    try:
        json.load(response)
    except ValueError as e:
        ctx.abort_operation('REST service returned malformed JSON: {0}'
                            .format(e))


ctx.logger.info('Starting Cloudify REST Service...')
utils.start_service(REST_SERVICE_NAME)

utils.systemd.verify_alive(REST_SERVICE_NAME)

restservice_url = 'http://{0}:{1}'.format('127.0.0.1', 8100)
utils.verify_service_http(REST_SERVICE_NAME, restservice_url)
verify_restservice(restservice_url)
