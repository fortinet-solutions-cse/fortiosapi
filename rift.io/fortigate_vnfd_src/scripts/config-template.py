#!/usr/bin/env python
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
''' This script must be called with the following patern
    ./config-template.py -d \
   '{"host":"<rw_mgmt_ip>","user":"admin","passwd":"", \
    "port2":"<rw_connection_point_name fortigate/cp1>", 
    "port3":"<rw_connection_point_name fortigate/cp2>", 
    "port4":"<rw_connection_point_name fortigate/cp3>", 
    "port5":"<rw_connection_point_name fortigate/cp4>" 
}'

To test directly:
./config-template.py -d    '{"host":"10.10.10.14","user":"admin","passwd":"", \
    "port2":"10.0.2.2", 
    "port3":"10.0.3.3", 
    "port4":"10.0.4.4", 
    "port5":"10.0.5.5"}'

./config-template.py -d  '{"host": "10.10.10.24", "user": "admin", "passwd": "", "port2": "10.0.2.2", "port3": "10.0.3.3","port4": "10.0.4.4","port5": "10.0.5.5"}'


'''


from fortigateconf import FortiOSConf
import argparse
parser = argparse.ArgumentParser()

parser.add_argument('-d', '--my-dict', type=str)
args = parser.parse_args()

import json
import logging
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortinetconflib')
hdlr = logging.FileHandler('/var/tmp/config-template.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)




print (args.my_dict)
d = json.loads(args.my_dict)

fgt = FortiOSConf()
fgt.login(d['host'],d['user'],d['passwd'])

for p in ["port2", "port3", "port4"]:   
    print (p)
    ip= d[p] + " 255.255.255.0"
    data = {
        "name": p,
        "mode": "static",
        "ip": ip,
        "allowaccess":"ping",
        "vdom":"root"
    }
    fgt.set('system','interface', vdom="root", data=data)

fgt.logout()


