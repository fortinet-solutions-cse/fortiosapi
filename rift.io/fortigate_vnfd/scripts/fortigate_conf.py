#!/usr/bin/env python3

############################################################################
# Copyright 2016 RIFT.IO Inc                                               #
#                                                                          #
# Licensed under the Apache License, Version 2.0 (the "License");          #
# you may not use this file except in compliance with the License.         #
# You may obtain a copy of the License at                                  #
#                                                                          #
#     http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                          #
# Unless required by applicable law or agreed to in writing, software      #
# distributed under the License is distributed on an "AS IS" BASIS,        #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. #
# See the License for the specific language governing permissions and      #
# limitations under the License.                                           #
############################################################################


import argparse
import logging
import os
import subprocess
import sys
import time

import yaml


def ping_set_rate(yaml_cfg, logger):
    '''Use curl and set traffic rate on ping vnf'''

    def set_rate(mgmt_ip, port, rate):
        curl_cmd = '''curl -D /dev/null \
    -H "Accept: application/vnd.yang.data+xml" \
    -H "Content-Type: application/vnd.yang.data+json" \
    -X POST \
    -d "{{ \\"rate\\":{ping_rate} }}" \
    http://{ping_mgmt_ip}:{ping_mgmt_port}/api/v1/ping/rate
'''.format(ping_mgmt_ip=mgmt_ip,
           ping_mgmt_port=port,
           ping_rate=rate)

        logger.debug("Executing cmd: %s", curl_cmd)
        subprocess.check_call(curl_cmd, shell=True)

    # Get the ping rate
    rate = yaml_cfg['parameter']['rate']

    # Set ping rate
    for index, vnfr in yaml_cfg['vnfr'].items():
        logger.debug("VNFR {}: {}".format(index, vnfr))

        # Check if it is pong vnf
        if 'ping_vnfd' in vnfr['name']:
            vnf_type = 'ping'
            port = 18888
            set_rate(vnfr['mgmt_ip_address'], port, rate)
            break

def main(argv=sys.argv[1:]):
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("yaml_cfg_file", type=argparse.FileType('r'))
        parser.add_argument("-q", "--quiet", dest="verbose", action="store_false")
        args = parser.parse_args()

        run_dir = os.path.join(os.environ['RIFT_INSTALL'], "var/run/rift")
        if not os.path.exists(run_dir):
            os.makedirs(run_dir)
        log_file = "{}/ping_set_rate-{}.log".format(run_dir, time.strftime("%Y%m%d%H%M%S"))
        logging.basicConfig(filename=log_file, level=logging.DEBUG)
        logger = logging.getLogger()

    except Exception as e:
        print("Exception in {}: {}".format(__file__, e))
        sys.exit(1)

    try:
        ch = logging.StreamHandler()
        if args.verbose:
            ch.setLevel(logging.DEBUG)
        else:
            ch.setLevel(logging.INFO)

        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    except Exception as e:
        logger.exception(e)
        raise e

    try:
        yaml_str = args.yaml_cfg_file.read()
        # logger.debug("Input YAML file:\n{}".format(yaml_str))
        yaml_cfg = yaml.load(yaml_str)
        logger.debug("Input YAML: {}".format(yaml_cfg))

        ping_set_rate(yaml_cfg, logger)

    except Exception as e:
        logger.exception(e)
        raise e

if __name__ == "__main__":
    main()
