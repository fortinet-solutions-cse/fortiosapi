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

# AMQP broker configuration for agents and manager
# Primarily used by celery, so provided with variables it understands
import json
import os
import ssl

from cloudify import constants

workdir_path = os.getenv('CELERY_WORK_DIR')
if workdir_path is None:
    # We are not in an appropriately configured celery environment
    config = {}
else:
    conf_file_path = os.path.join(workdir_path, 'broker_config.json')
    if os.path.isfile(conf_file_path):
        with open(conf_file_path) as conf_handle:
            conf_file = conf_handle.read()
            config = json.loads(conf_file)
    else:
        config = {}

# Provided as variables for retrieval by amqp_client and logger as required
broker_ssl_enabled = config.get('broker_ssl_enabled', False)
broker_cert_path = config.get('broker_cert_path', '')
broker_username = config.get('broker_username', 'guest')
broker_password = config.get('broker_password', 'guest')
broker_hostname = config.get('broker_hostname', 'localhost')

if broker_ssl_enabled:
    BROKER_USE_SSL = {
        'ca_certs': broker_cert_path,
        'cert_reqs': ssl.CERT_REQUIRED,
    }
    broker_port = constants.BROKER_PORT_SSL
else:
    broker_port = constants.BROKER_PORT_NO_SSL

# This is held in the config to avoid the password appearing in ps listings
BROKER_URL = 'amqp://{username}:{password}@{hostname}:{port}'.format(
    username=broker_username,
    password=broker_password,
    hostname=broker_hostname,
    port=broker_port,
)
CELERY_RESULT_BACKEND = BROKER_URL
CELERY_TASK_RESULT_EXPIRES = 600
CELERYD_PREFETCH_MULTIPLIER = 0
CELERY_ACKS_LATE = True
