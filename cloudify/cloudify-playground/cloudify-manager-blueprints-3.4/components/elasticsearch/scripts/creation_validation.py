#!/usr/bin/env python

import urllib2
import urlparse
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


ES_SERVICE_NAME = 'elasticsearch'


def verify_properties():
    """Compare node properties and decide if upgrading is allowed."""
    changed = utils.changed_upgrade_properties(ES_SERVICE_NAME)

    if 'es_heap_size' in changed:
        bootstrap_heap_size, upgrade_heap_size = changed['es_heap_size']
        bootstrap_heap_size = utils.parse_jvm_heap_size(bootstrap_heap_size)
        upgrade_heap_size = utils.parse_jvm_heap_size(upgrade_heap_size)

        if upgrade_heap_size < bootstrap_heap_size:
            ctx.abort_operation('Upgrading a Cloudify Manager with '
                                'Elasticsearch Heap Size lower than what it '
                                'was initially bootstrapped with is not '
                                'allowed.')


def verify_elasticsearch_running(url):
    """Check that ES is running, and that it contains the provider context.

    This is a sanity check that the manager we're upgrading was bootstrapped
    correctly.
    """
    provider_context_url = urlparse.urljoin(url, 'cloudify_storage/'
                                                 'provider_context/CONTEXT')
    try:
        urllib2.urlopen(provider_context_url)
    except urllib2.URLError as e:
        ctx.abort_operation('ES returned an error when getting the provider '
                            'context: {0}'.format(e))
        raise


if utils.is_upgrade:
    utils.validate_upgrade_directories(ES_SERVICE_NAME)
    install_properties = utils.ctx_factory.get(ES_SERVICE_NAME)
    ES_ENDPOINT_IP = install_properties['es_endpoint_ip']
    ES_ENDPOINT_PORT = install_properties['es_endpoint_port']
    if not ES_ENDPOINT_IP:
        ES_ENDPOINT_IP = '127.0.0.1'
        utils.systemd.verify_alive(ES_SERVICE_NAME, append_prefix=False)

    elasticsearch_url = 'http://{0}:{1}'.format(ES_ENDPOINT_IP,
                                                ES_ENDPOINT_PORT)
    verify_elasticsearch_running(elasticsearch_url)
    verify_properties()
