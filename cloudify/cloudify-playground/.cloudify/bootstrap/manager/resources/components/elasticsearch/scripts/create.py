#!/usr/bin/env python

import os
import urllib2
import json
import time
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONFIG_PATH = "components/elasticsearch/config"
ES_SERVICE_NAME = 'elasticsearch'

DUMP_FILE_PATH = os.path.join(utils.ES_UPGRADE_DUMP_PATH, 'es_dump')
DUMP_SUCCESS_FLAG = os.path.join(utils.ES_UPGRADE_DUMP_PATH, 'es_dump_success')

ctx_properties = utils.ctx_factory.create(ES_SERVICE_NAME)


def http_request(url, data=None, method='PUT'):
    request = urllib2.Request(url, data=data)
    request.get_method = lambda: method
    try:
        return urllib2.urlopen(request)
    except urllib2.URLError as e:
        reqstring = url + (' ' + data if data else '')
        ctx.logger.info('Failed to {0} {1} (reason: {2})'.format(
            method, reqstring, e.reason))


def _configure_elasticsearch(host, port):

    storage_endpoint = 'http://{0}:{1}/cloudify_storage/'.format(host, port)
    storage_settings = json.dumps({
        "settings": {
            "analysis": {
                "analyzer": {
                    "default": {"tokenizer": "whitespace"}
                }
            }
        }
    })

    ctx.logger.info('Deleting `cloudify_storage` index if exists...')
    http_request(storage_endpoint, method='DELETE')
    ctx.logger.info('Creating `cloudify_storage` index...')
    http_request(storage_endpoint, storage_settings, 'PUT')

    blueprint_mapping_endpoint = storage_endpoint + 'blueprint/_mapping'
    blueprint_mapping = json.dumps({
        "blueprint": {
            "properties": {
                "plan": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring blueprint mapping...')
    http_request(blueprint_mapping_endpoint, blueprint_mapping, 'PUT')

    deployment_mapping_endpoint = storage_endpoint + 'deployment/_mapping'
    deployment_mapping = json.dumps({
        "deployment": {
            "properties": {
                "workflows": {"enabled": False},
                "inputs": {"enabled": False},
                "policy_type": {"enabled": False},
                "policy_triggers": {"enabled": False},
                "groups": {"enabled": False},
                "outputs": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring deployment mapping...')
    http_request(deployment_mapping_endpoint, deployment_mapping, 'PUT')

    execution_mapping_endpoint = storage_endpoint + 'execution/_mapping'
    execution_mapping = json.dumps({
        "execution": {
            "properties": {
                "parameters": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring execution mapping...')
    http_request(execution_mapping_endpoint, execution_mapping, 'PUT')

    node_mapping_endpoint = storage_endpoint + 'node/_mapping'
    node_mapping = json.dumps({
        "node": {
            "_id": {"path": "id"},
            "properties": {
                "types": {"type": "string", "index_name": "type"},
                "properties": {"enabled": False},
                "operations": {"enabled": False},
                "relationships": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring node mapping...')
    http_request(node_mapping_endpoint, node_mapping, 'PUT')

    node_instance_mapping_endpoint = \
        storage_endpoint + 'node_instance/_mapping'
    node_instance_mapping = json.dumps({
        "node_instance": {
            "_id": {"path": "id"},
            "properties": {
                "runtime_properties": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring node instance mapping...')
    http_request(node_instance_mapping_endpoint, node_instance_mapping, 'PUT')

    deployment_modification_mapping_endpoint = \
        storage_endpoint + 'deployment_modification/_mapping'
    deployment_modification_mapping = json.dumps({
        "deployment_modification": {
            "_id": {"path": "id"},
            "properties": {
                "modified_nodes": {"enabled": False},
                "node_instances": {"enabled": False},
                "context": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring deployment modification mapping...')
    http_request(
        deployment_modification_mapping_endpoint,
        deployment_modification_mapping, 'PUT')

    deployment_update_mapping_endpoint = \
        storage_endpoint + 'deployment_update/_mapping'
    deployment_update_mapping = json.dumps({
        "deployment_update": {
            "_id": {"path": "id"},
            "properties": {
                "deployment_update_nodes": {"enabled": False},
                "deployment_update_node_instances": {"enabled": False},
                "deployment_update_deployment": {"enabled": False},
                "deployment_plan": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring deployment update mapping...')
    http_request(
        deployment_update_mapping_endpoint,
        deployment_update_mapping, 'PUT')


def _configure_index_rotation():
    ctx.logger.info('Configuring Elasticsearch Index Rotation cronjob for '
                    'logstash-YYYY.mm.dd index patterns...')
    utils.deploy_blueprint_resource(
        'components/elasticsearch/scripts/rotate_es_indices',
        '/etc/cron.daily/rotate_es_indices', ES_SERVICE_NAME)
    utils.chown('root', 'root', '/etc/cron.daily/rotate_es_indices')
    # VALIDATE!
    utils.sudo('chmod +x /etc/cron.daily/rotate_es_indices')


def _install_elasticsearch():
    es_java_opts = ctx_properties['es_java_opts']
    es_heap_size = ctx_properties['es_heap_size']

    es_source_url = ctx_properties['es_rpm_source_url']
    es_curator_rpm_source_url = \
        ctx_properties['es_curator_rpm_source_url']

    # this will be used only if elasticsearch-curator is not installed via
    # an rpm and an internet connection is available
    es_curator_version = "3.2.3"

    es_home = "/opt/elasticsearch"
    es_logs_path = "/var/log/cloudify/elasticsearch"
    es_conf_path = "/etc/elasticsearch"
    es_unit_override = "/etc/systemd/system/elasticsearch.service.d"
    es_scripts_path = os.path.join(es_conf_path, 'scripts')

    ctx.logger.info('Installing Elasticsearch...')
    utils.set_selinux_permissive()

    utils.copy_notice('elasticsearch')
    utils.mkdir(es_home)
    utils.mkdir(es_logs_path)

    utils.yum_install(es_source_url, service_name=ES_SERVICE_NAME)

    ctx.logger.info('Chowning {0} by elasticsearch user...'.format(
        es_logs_path))
    utils.chown('elasticsearch', 'elasticsearch', es_logs_path)

    ctx.logger.info('Creating systemd unit override...')
    utils.mkdir(es_unit_override)
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'restart.conf'),
        os.path.join(es_unit_override, 'restart.conf'), ES_SERVICE_NAME)

    ctx.logger.info('Deploying Elasticsearch Configuration...')
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'elasticsearch.yml'),
        os.path.join(es_conf_path, 'elasticsearch.yml'), ES_SERVICE_NAME)
    utils.chown('elasticsearch', 'elasticsearch',
                os.path.join(es_conf_path, 'elasticsearch.yml'))

    ctx.logger.info('Deploying elasticsearch logging configuration file...')
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'logging.yml'),
        os.path.join(es_conf_path, 'logging.yml'), ES_SERVICE_NAME)
    utils.chown('elasticsearch', 'elasticsearch',
                os.path.join(es_conf_path, 'logging.yml'))

    ctx.logger.info('Creating Elasticsearch scripts folder and '
                    'additional external Elasticsearch scripts...')
    utils.mkdir(es_scripts_path)
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'scripts', 'append.groovy'),
        os.path.join(es_scripts_path, 'append.groovy'),
        ES_SERVICE_NAME
    )

    ctx.logger.info('Setting Elasticsearch Heap Size...')
    # we should treat these as templates.
    utils.replace_in_file(
        '(?:#|)ES_HEAP_SIZE=(.*)',
        'ES_HEAP_SIZE={0}'.format(es_heap_size),
        '/etc/sysconfig/elasticsearch')

    if es_java_opts:
        ctx.logger.info('Setting additional JAVA_OPTS...')
        utils.replace_in_file(
            '(?:#|)ES_JAVA_OPTS=(.*)',
            'ES_JAVA_OPTS={0}'.format(es_java_opts),
            '/etc/sysconfig/elasticsearch')

    ctx.logger.info('Setting Elasticsearch logs path...')
    utils.replace_in_file(
        '(?:#|)LOG_DIR=(.*)',
        'LOG_DIR={0}'.format(es_logs_path),
        '/etc/sysconfig/elasticsearch')
    utils.replace_in_file(
        '(?:#|)ES_GC_LOG_FILE=(.*)',
        'ES_GC_LOG_FILE={0}'.format(os.path.join(es_logs_path, 'gc.log')),
        '/etc/sysconfig/elasticsearch')
    utils.logrotate(ES_SERVICE_NAME)

    ctx.logger.info('Installing Elasticsearch Curator...')
    if not es_curator_rpm_source_url:
        ctx.install_python_package('elasticsearch-curator=={0}'.format(
            es_curator_version))
    else:
        utils.yum_install(es_curator_rpm_source_url,
                          service_name=ES_SERVICE_NAME)

    _configure_index_rotation()

    # elasticsearch provides a systemd init env. we just enable it.
    utils.systemd.enable(ES_SERVICE_NAME, append_prefix=False)


def _wait_for_shards(port, ip):
    """Wait for activation of all available shards in Elasticsearch.

    After Elasticsearch is installed and first time started there is short time
    when shards, if created, are not started. If someone would access ES during
    that time (e.g. by creating snapshot) he will get error
    'SearchPhaseExecutionException[Failed to execute phase [init_scan], all
    shards failed]'.

    :param port: Elasticsearch port
    :param ip: Ip to Elasticsearch
    """
    ctx.logger.info('Waiting for shards to be active...')
    shards_check_timeout = 60
    start = time.time()

    url = 'http://{ip}:{port}/*/_search_shards'.format(ip=ip, port=port)
    while True:
        all_shards_started = True
        try:
            out = urllib2.urlopen(url)
            shards = json.load(out)['shards']
            for shard in shards:
                all_shards_started = all_shards_started and \
                    (shard[0]['state'] == 'STARTED')
        except urllib2.URLError as e:
            ctx.abort_operation('Failed to retrieve information about '
                                'Elasticsearch shards: {0}'.format(e.reason))

        if all_shards_started:
            return
        time.sleep(1)
        if time.time() - start > shards_check_timeout:
            inactive = [s[0] for s in shards if s[0]['state'] != 'STARTED']
            ctx.abort_operation('Elasticsearch shards check timed out. '
                                'Inactive shards: {0}'.format(inactive))


def main():

    es_endpoint_ip = ctx_properties['es_endpoint_ip']
    es_endpoint_port = ctx_properties['es_endpoint_port']

    if utils.is_upgrade:
        dump_upgrade_data()

    if not es_endpoint_ip:
        es_endpoint_ip = ctx.instance.host_ip
        _install_elasticsearch()
        utils.systemd.restart(ES_SERVICE_NAME, append_prefix=False)
        utils.wait_for_port(es_endpoint_port, es_endpoint_ip)
        _configure_elasticsearch(host=es_endpoint_ip, port=es_endpoint_port)
        _wait_for_shards(es_endpoint_port, es_endpoint_ip)

        utils.clean_var_log_dir('elasticsearch')
    else:
        ctx.logger.info('External Elasticsearch Endpoint provided: '
                        '{0}:{1}...'.format(es_endpoint_ip, es_endpoint_port))
        time.sleep(5)
        utils.wait_for_port(es_endpoint_port, es_endpoint_ip)
        ctx.logger.info('Checking if \'cloudify_storage\' '
                        'index already exists...')

        if http_request('http://{0}:{1}/cloudify_storage'.format(
                es_endpoint_ip, es_endpoint_port), method='HEAD').code == 200:
            ctx.abort_operation('\'cloudify_storage\' index already exists on '
                                '{0}, terminating bootstrap...'.format(
                                    es_endpoint_ip))
        _configure_elasticsearch(host=es_endpoint_ip, port=es_endpoint_port)

    if utils.is_upgrade or utils.is_rollback:
        restore_upgrade_data(es_endpoint_ip, es_endpoint_port)

    if not es_endpoint_port:
        utils.systemd.stop(ES_SERVICE_NAME, append_prefix=False)

    ctx.instance.runtime_properties['es_endpoint_ip'] = es_endpoint_ip


def _get_es_install_port():
    es_props = utils.ctx_factory.load_rollback_props(ES_SERVICE_NAME)
    return es_props['es_endpoint_port']


def _get_es_install_endpoint():
    es_props = utils.ctx_factory.load_rollback_props(ES_SERVICE_NAME)
    if es_props['es_endpoint_ip']:
        es_endpoint = es_props['es_endpoint_ip']
    else:
        es_endpoint = ctx.instance.host_ip
    return es_endpoint


def dump_upgrade_data():

    if os.path.exists(DUMP_SUCCESS_FLAG):
        return

    endpoint = _get_es_install_endpoint()
    port = _get_es_install_port()
    storage_endpoint = 'http://{0}:{1}/cloudify_storage'.format(endpoint,
                                                                port)
    types = ['provider_context', 'snapshot']
    ctx.logger.info('Dumping upgrade data: {0}'.format(types))
    type_values = []
    for _type in types:
        res = http_request('{0}/_search?q=_type:{1}&size=10000'
                           .format(storage_endpoint, _type),
                           method='GET')
        if not res.code == 200:
            ctx.abort_operation('Failed fetching type {0} from '
                                'cloudify_storage index'.format(_type))

        body = res.read()
        hits = json.loads(body)['hits']['hits']
        for hit in hits:
            type_values.append(hit)

    utils.mkdir(utils.ES_UPGRADE_DUMP_PATH, use_sudo=False)
    with open(DUMP_FILE_PATH, 'w') as f:
        for item in type_values:
            f.write(json.dumps(item) + os.linesep)

    # marker file to indicate dump has succeeded
    with open(DUMP_SUCCESS_FLAG, 'w') as f:
        f.write('success')


def restore_upgrade_data(es_endpoint_ip, es_endpoint_port):
    bulk_endpoint = 'http://{0}:{1}/_bulk'.format(es_endpoint_ip,
                                                  es_endpoint_port)
    with open(DUMP_FILE_PATH) as f:
        all_data = ''
        for line in f.readlines():
            all_data += _create_index_request(line)
    ctx.logger.info('Restoring elasticsearch data')
    res = http_request(url=bulk_endpoint, data=all_data, method='POST')
    if res.code != 200:
        ctx.abort_operation('Failed restoring elasticsearch data.')
    ctx.logger.info('Elasticsearch data was successfully restored')


def _create_index_request(line):
    item = json.loads(line)
    source = json.dumps(item['_source'])
    metadata = _only_types(item, ['_type', '_id', '_index'])
    action_and_meta_data = json.dumps({'index': metadata})
    return action_and_meta_data + os.linesep + source + os.linesep


def _only_types(d, args):
    return {key: d[key] for key in d.keys() if key in args}


main()
