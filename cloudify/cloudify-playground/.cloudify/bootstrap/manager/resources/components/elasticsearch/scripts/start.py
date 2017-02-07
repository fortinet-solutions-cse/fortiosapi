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

ES_SERVICE_NAME = 'elasticsearch'
ctx_properties = utils.ctx_factory.get(ES_SERVICE_NAME)
ES_ENDPOINT_IP = ctx_properties['es_endpoint_ip']
ES_ENDPOINT_PORT = ctx_properties['es_endpoint_port']


def _examine_status_response(response):
    """Check if the status response from elasticsearch is correct.

    A correct response has a status of 200, and also returns a JSON object
    with {'status': 200}.
    Elasticsearch doesn't start up immediately, so this retries a few times.
    """
    if response.code != 200:
        return False

    parsed_response = json.load(response)

    return parsed_response['status'] == 200


def check_index_exists(url, index_name='cloudify_storage'):
    """Check that the cloudify_storage ES index exists."""
    index_url = urlparse.urljoin(url, index_name)
    try:
        return urllib2.urlopen(index_url)
    except urllib2.URLError as e:
        if e.code == 404:
            ctx.abort_operation('The index {0} does not exist in ES'.format(
                index_name))
        else:
            ctx.abort_operation('Invalid ES response: {0}'.format(e))


if not ES_ENDPOINT_IP:
    ctx.logger.info('Starting Elasticsearch Service...')
    utils.start_service(ES_SERVICE_NAME, append_prefix=False)
    ES_ENDPOINT_IP = '127.0.0.1'
    utils.systemd.verify_alive(ES_SERVICE_NAME, append_prefix=False)

elasticsearch_url = 'http://{0}:{1}/'.format(ES_ENDPOINT_IP,
                                             ES_ENDPOINT_PORT)
utils.verify_service_http(ES_SERVICE_NAME, elasticsearch_url,
                          _examine_status_response)
check_index_exists(elasticsearch_url)
