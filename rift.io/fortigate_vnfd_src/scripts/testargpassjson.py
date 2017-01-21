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

parser.add_argument('-s', '--my-str', type=str)
args = parser.parse_args()

import json, pprint
import logging
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortinetconflib')
hdlr = logging.FileHandler('/var/tmp/config-template.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)
pp = pprint.PrettyPrinter(indent=4)

mystr= args.my_str

print ("arg receivd : %s" % mystr)
commands = mystr.split("\\n")
# multi line is accepted with \n to separate then converted because juju does not allow advanced types like list or json :(
mydata={}
for line in commands:
    key=line.split(":")[0].strip()
    value=line.split(":")[1].strip()
    mydata[key]=value
    
pp.pprint (mydata)
'''
strjson="""{
{},
\}""".format("\n".join(commands))


print (strjson)


'''

data = {
    #         "action" : "add",
    "seq-num" :"8",
    "dst": "10.10.30.0 255.255.255.0",
    "device": "port2",
    "gateway": "192.168.40.254",
}
pp.pprint(data)
 
