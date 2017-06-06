#!/usr/bin/env python
# Copyright 2015 Fortinet, Inc.
#
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

###################################################################
#
# fortiosapi.py unit test rely on a local VM so can verify from
# the console (pexpect)
# 
#
###################################################################
import unittest
from fortiosapi import FortiOSAPI
import sys
import pprint
import json
from argparse import Namespace
import pexpect
import yaml
import logging
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortiosapi'
hdlr = logging.FileHandler('/var/tmp/testfortiosapi.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)

#Option parsing
parser = argparse.ArgumentParser(description="Can push the configuration for virsh ")
parser.add_argument('-c', action="store", dest="conffile", default='virsh.yaml')
args = parser.parse_args()

fgt = FortiOSAPI()
                           
def json2obj(data):
    return json.loads(data, object_hook=lambda d: Namespace(**d))

with open(args.conffile, 'r') as f:
    conf = yaml.load(f)
                           
class TestFortinetRestAPI(unittest.TestCase):
 
    def setUp(self):
        # must use pexepct to reset VM to factory
        pass
 
    def test_login(self):
        self.assertEqual( multiply(3,4), 12)
 
    def test_get(self):
        self.assertEqual( multiply('a',3), 'aaa')
 
if __name__ == '__main__':
    unittest.main()

def json2obj(data):
    return json.loads(data, object_hook=lambda d: Namespace(**d))


def main():
    # Login to the FGT ip
    fgt.debug('on')
    fgt.login('192.168.40.8','admin','')
    data = {
  #         "action" : "add",
           "seq-num" :"8",
           "dst": "10.10.30.0 255.255.255.0",
           "device": "port2",
           "gateway": "192.168.40.254",
        }
    pp = pprint.PrettyPrinter(indent=4)
    d=json2obj(json.dumps(data))
    pp.pprint(fgt.get_name_path_dict( vdom="root"))
  #  resp = fgt.schema('diagnose__tree__','debug', vdom="root")
  #  pp.pprint(resp)
    resp = fgt.post('diagnose__tree__','debug', vdom="root", mkey="enable")
    
    pp.pprint(resp)

    fgt.logout()
