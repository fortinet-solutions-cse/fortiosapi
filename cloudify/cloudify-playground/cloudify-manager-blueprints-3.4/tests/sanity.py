########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import json
import logging
import os
import urllib2
import time

import boto.ec2
from boto import exception as boto_exception

from retrying import retry
from fabric.api import settings as fabric_settings
from fabric.api import run as fabric_run


REGION = 'us-east-1'
CENTOS_7_AMI_ID = 'ami-96a818fe'
USER = 'centos'
INSTANCE_TYPE = 'm3.large'
RESOURCE_NAME = 'cloudify-bootstrap-sanity-travis'

HELLO_WORLD_URL = 'https://github.com/cloudify-cosmo/' \
                  'cloudify-hello-world-example.git'
BLUEPRINT_ID = 'hello-world'
DEPLOYMENT_ID = 'hello1'
HELLO_WORLD_PORT = 8080

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
lgr = logging.getLogger('sanity')
lgr.setLevel(logging.INFO)

aws_access_key = os.environ['AWS_ACCESS_KEY']
aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
ssh_public_key = os.environ['SSH_PUBLIC_KEY']
ssh_private_key = os.environ['SSH_PRIVATE_KEY']


def delete_security_group(conn):
    try:
        sgs = conn.get_all_security_groups(groupnames=[RESOURCE_NAME])
        lgr.info('Found security groups: {0}'.format(sgs))
        for sg in sgs:
            lgr.info('Deleting security group: {0}'.format(sg))
            sg.delete()
    except boto_exception.EC2ResponseError as e:
        lgr.warning('Cannot find Security group {0} [e.status={1}]'.format(
            RESOURCE_NAME,
            e.status))
        if e.status != 400:
            raise
        lgr.warning('Security group {0} not found, ignoring...'.format(
            RESOURCE_NAME))


def create_security_group(conn):
    lgr.info('Creating security group...')
    sg = conn.create_security_group(RESOURCE_NAME, RESOURCE_NAME)
    sg.authorize('tcp', 80, 80, '0.0.0.0/0')
    sg.authorize('tcp', 22, 22, '0.0.0.0/0')
    sg.authorize('tcp', HELLO_WORLD_PORT, HELLO_WORLD_PORT, '0.0.0.0/0')
    return sg


@retry(wait_fixed=10000, stop_max_attempt_number=60)
def wait_for_instance_status(instance, expected_status):
    status = instance.update()
    if status != expected_status:
        msg = 'Instance status is expected to be {0} but is {1}. '\
            'retrying...'.format(expected_status, status)
        lgr.warning(msg)
        raise RuntimeError(msg)


def delete_instance(conn):
    instance = get_instance(conn)
    if instance:
        lgr.info('Terminating instance: {0}'.format(instance))
        instance.terminate()
        wait_for_instance_status(instance, 'terminated')


@retry(wait_fixed=10000, stop_max_attempt_number=60)
def verify_connectivity_to_instance(ip_address, key_filename):
    port = 22
    try:
        lgr.info('Verifying SSH connectivity to: {0}:{1}'.format(
            ip_address, port))
        with fabric_settings(host_string='{0}:{1}'.format(ip_address, port),
                             user=USER,
                             key_filename=key_filename):
            fabric_run('echo "hello"', timeout=10)
    except Exception as e:
        lgr.warning('Unable to connect: {0}'.format(str(e)))
        raise


def create_instance(conn):
    lgr.info('Creating instance...')
    reservation = conn.run_instances(CENTOS_7_AMI_ID,
                                     key_name=RESOURCE_NAME,
                                     instance_type=INSTANCE_TYPE,
                                     security_groups=[RESOURCE_NAME])
    instance = reservation.instances[0]
    wait_for_instance_status(instance, 'running')
    lgr.info('Instance created, Adding tags...')
    instance.add_tag('Name', RESOURCE_NAME)


def delete_keypair(conn):
    keys = conn.get_all_key_pairs(keynames=[RESOURCE_NAME])
    lgr.info('Found keys: {0}'.format(keys))
    for key in keys:
        lgr.info('Deleting key: {0}'.format(key))
        key.delete()


def create_keypair(conn):
    lgr.info('Creating key pair...')
    conn.import_key_pair(RESOURCE_NAME, ssh_public_key)


def get_instance(conn):
    instances = conn.get_all_instances(filters={
        'tag:Name': RESOURCE_NAME, 'instance-state-name': 'running'})
    if len(instances) == 1:
        return instances[0].instances[0]
    elif len(instances) > 1:
        raise RuntimeError(
            'Illegal state - found too many instances: {0}'.format(instances))
    else:
        return None


def get_instance_ip_address(conn):
    instance = get_instance(conn)
    ip_address = instance.ip_address
    if not ip_address:
        msg = 'ip_address not set on instance. retrying...'
        lgr.warning(msg)
        raise RuntimeError(msg)
    return ip_address


def write_ssh_key_file():
    lgr.info('Writing SSH key file...')
    key_file_path = os.path.join(os.getcwd(), 'key.pem')
    with open(key_file_path, 'w') as f:
        f.write(ssh_private_key.replace('\\n', os.linesep))
    return key_file_path


def execute(command):
    r = os.system(command)
    if r != 0:
        raise RuntimeError('Command: {0} exited with {1}'.format(command, r))


def run_test(conn, ip_address, key_file_path):
    lgr.info('Bootstrapping a Cloudify manager...')
    os.system('cfy --version')
    lgr.info('Writing inputs file...')
    inputs = json.dumps({
        'public_ip': ip_address,
        'private_ip': 'localhost',
        'ssh_user': USER,
        'ssh_key_filename': key_file_path,
        'agents_user': USER
    }, indent=2)
    lgr.info('Bootstrap inputs: {0}'.format(inputs))
    with open('inputs.json', 'w') as f:
        f.write(inputs)

    execute('cfy init')
    execute('cfy bootstrap -p ../simple-manager-blueprint.yaml '
            '-i inputs.json --install-plugins')

    generated_key_path = '/root/.ssh/key.pem'
    lgr.info('Generating SSH keys for hello-world deployment...')
    with fabric_settings(host_string='{0}:{1}'.format(ip_address, 22),
                         user=USER,
                         key_filename=key_file_path,
                         timeout=30):
        fabric_run('sudo ssh-keygen -f {0} -q -t rsa -N ""'.format(
            generated_key_path))
        fabric_run('sudo cat {0}.pub >> ~/.ssh/authorized_keys'.format(
            generated_key_path))

    execute('git clone {0}'.format(HELLO_WORLD_URL))

    webserver_port = HELLO_WORLD_PORT
    hello_inputs = json.dumps({
        'server_ip': 'localhost',
        'agent_user': USER,
        'agent_private_key_path': generated_key_path,
        'webserver_port': webserver_port
    })
    with open('hello-inputs.json', 'w') as f:
        f.write(hello_inputs)

    execute('cfy blueprints upload -b {0} -p '
            'cloudify-hello-world-example/singlehost-blueprint.yaml'.format(
                BLUEPRINT_ID))
    execute('cfy deployments create -b {0} -d {1} -i hello-inputs.json'.format(
        BLUEPRINT_ID, DEPLOYMENT_ID))

    # Sleep some time because of CFY-4066
    lgr.info('Waiting for 15 seconds before executing install workflow...')
    time.sleep(15)
    execute('cfy executions start -d {0} -w install'.format(DEPLOYMENT_ID))

    url = 'http://{0}:{1}'.format(ip_address, webserver_port)
    lgr.info('Verifying deployment at {0}'.format(url))
    urllib2.urlopen(url).read()
    lgr.info('Deployment is running!')


if __name__ == '__main__':

    lgr.info('Starting bootstrap sanity test...')

    conn = boto.ec2.connect_to_region(
        REGION,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_access_key)

    key_file_path = write_ssh_key_file()

    delete_instance(conn)
    delete_security_group(conn)
    delete_keypair(conn)

    create_keypair(conn)
    create_security_group(conn)
    create_instance(conn)

    ip_address = get_instance_ip_address(conn)
    verify_connectivity_to_instance(ip_address, key_file_path)

    run_test(conn, ip_address, key_file_path)
