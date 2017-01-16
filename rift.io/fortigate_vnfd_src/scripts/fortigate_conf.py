#!/usr/bin/env python3

# Copyright 2017 Fortinet, Inc.
#
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#


import argparse
import logging
import os
import subprocess
import sys
import time
import re
import json
from fortigateconf import FortiOSConf
import yaml
fgt = FortiOSConf()


def conf_interface_from_cps(yaml_cfg, logger):

#    user = yaml_cfg['parameter']['user']
    user = "admin"
    passwd = ""

    # Set ping rate
    for index, vnfr in yaml_cfg['vnfr'].items():
        logger.debug("VNFR {}: {}".format(index, vnfr))

        # Check if it is a fortigate vnf
        #
        if 'fgtvdu' in  vnfr['vdur'][0]['name']:
            host = vnfr['mgmt_ip_address']
            fgt.login(host,user,passwd)
            #todo check acces to API ok (license validation)
            for cp in vnfr['connection_point']:
                fortiport = "port"+str(int(re.sub("\D", "",cp['name'])))
                ### get the number of connection port minus 1 to find fortigate por
                
                data = {
                    "name": fortiport,
                    "interface": fortiport,
                    "mode": "static",
                    "ip": cp['ip_address']+" 255.255.255.0",
                    "allowaccess":"ping",
                    "vdom":"root"
                }
                logger.debug("fgt.set data: {}".format(data))
                resp = fgt.set('system','interface', vdom="root", data=data)
                
                logger.debug("fgt.set resp: {}".format(resp))
                
            fgt.logout()

def main(argv=sys.argv[1:]):
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("yaml_cfg_file", type=argparse.FileType('r'))
        parser.add_argument("-q", "--quiet", dest="verbose", action="store_false")
        args = parser.parse_args()

        run_dir = os.path.join(os.environ['RIFT_INSTALL'], "var/run/rift")
        if not os.path.exists(run_dir):
            os.makedirs(run_dir)
        log_file = "{}/fortigate-conf-{}.log".format(run_dir, time.strftime("%Y%m%d%H%M%S"))
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

        conf_interface_from_cps(yaml_cfg, logger)

    except Exception as e:
        logger.exception(e)
        raise e

if __name__ == "__main__":
    main()
