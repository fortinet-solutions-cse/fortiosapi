#!/usr/bin/env python
import unittest

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
# user must be able to do all kvm/qemu function
# parameters in virsh.yaml or a file as a conf
# will use a fortios.qcow2 image create the vm and destroy it at the
# end this will allow to test a list of versions/products automated
#
###################################################################
from fortiosapi import FortiOSAPI
import sys
import os
import pprint
import json
import pexpect
import yaml
import logging
from packaging.version import Version
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortiosapi')
hdlr = logging.FileHandler('testfortiosapi.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)

fgt = FortiOSAPI()
                           
#def json2obj(data):
#    return json.loads(data, object_hook=lambda d: Namespace(**d))

virshconffile =  os.getenv('VIRSH_CONF_FILE', "virsh.yaml")
conf = yaml.load(open(virshconffile,'r'))
# when python35 pexepct will be fixed#child = pexpect.spawn('virsh console '+conf["sut"]["vmname"],logfile=open("testfortiosapi.lo", "w"))
child = pexpect.spawn('virsh console '+conf["sut"]["vmname"])
#child.logfile = sys.stdout
#TODO add the option to run on a remote VM with -c qemu+ssh://
fgt.debug('on')


class TestFortinetRestAPI(unittest.TestCase):

    # Note that, for Python 3 compatibility reasons, we are using spawnu and
    # importing unicode_literals (above). spawnu accepts Unicode input and
    # unicode_literals makes all string literals in this script Unicode by default.
    
    def setUp(self):
        pass
    
    def sendtoconsole(self, cmds):
        #sometime lock waiting for prompt
        child.sendline(str("\n "))
        #look for prompt or login
        r = child.expect(['.* login:','#'])
        if r == 0:
            child.send( "admin\n")
            child.expect("Password:")
            child.send(conf["sut"]["passwd"]+"\n")
            child.expect(' #')
        for line in cmds.splitlines():
            child.sendline(line+'\r')

    def test_00login(self):
        # adapt if using eval license or not
        if conf["sut"]["eval"] == "yes":
            fgt.https('off')
        else:
            fgt.https('on')
        self.assertEqual( fgt.login(conf["sut"]["ip"],conf["sut"]["user"],conf["sut"]["passwd"]) , None )
        
    def test_01logout_login(self):
        self.assertEqual( fgt.logout(), None)
        self.assertEqual( fgt.login(conf["sut"]["ip"],conf["sut"]["user"],conf["sut"]["passwd"]) , None )
                
    def test_setaccessperm(self):
        data = {
            "name": "port1",
            "allowaccess": "ping https ssh http fgfm snmp",
            "vdom":"root"
        }
        self.assertEqual(fgt.set('system','interface', vdom="root", data=data)['http_status'], 200)
        
    def test_setfirewalladdress(self):
        data = {
            "name": "all.acme.test",
            "wildcard-fqdn": "*.acme.test",
            "type": "wildcard-fqdn",
        }
        #ensure the seq 8 for route is not present
        cmds='''config firewall address
        delete all.acme.test
        end '''        
        self.sendtoconsole(cmds)
        self.assertEqual(fgt.set('firewall','address', vdom="root", data=data)['http_status'], 200)
#doing it a second time to test put instead of post
        self.assertEqual(fgt.set('firewall','address', vdom="root", data=data)['http_status'], 200)

    def test_posttorouter(self):
        data = {
            "seq-num": "8",
            "dst": "10.10.32.0 255.255.255.0",
            "device": "port1",
            "gateway": "192.168.40.252",
        }
        #ensure the seq 8 for route is not present
        cmds='''config router static
        delete 8
        end '''        
        self.sendtoconsole(cmds)
        self.assertEqual(fgt.post('router','static', vdom="root", data=data)['http_status'], 200)
        self.assertEqual(fgt.set ('router','static', vdom="root", data=data)['http_status'], 200)

       
    @unittest.expectedFailure
    def test_accesspermfail(self):
        data = {
            "name": "port1",
            "allowaccess": "ping https ssh http fgfm snmp",
            "vdom":"root"
        }
        self.assertEqual(fgt.set('system','interface', vdom="root", mkey='bad', data=data)['http_status'], 200, "broken")
        

    def test_02getsystemglobal(self):
        resp = fgt.get('system','global', vdom="global")
        fortiversion = resp['version']
        self.assertEqual(resp['status'], 'success')

    #should put a test on version to disable if less than 5.6 don't work decoration 
    #@unittest.skipIf(Version(fgt.get_version()) < Version('5.6'),
    #                 "not supported with fortios before 5.6")
    def test_is_license_valid(self):
        if Version(fgt.get_version()) > Version('5.6'):
            self.assertTrue(fgt.license()['results']['vm']['status'] == "vm_valid" or "vm_eval")
        else:
            self.assertTrue(True, "not supported before 5.6")

    def test_central_management(self):
        #This call does not have mkey test used to validate it does not blow up
        data = {
            "type": "fortimanager",
            "fmg": "10.210.67.18",
        }
        self.assertEqual(fgt.put('system','central-management', vdom="root",data=data)['status'], 'success')
        
        
    def test_monitorresources(self):
        self.assertEqual(fgt.monitor('system','vdom-resource', mkey='select', vdom="root")['status'], 'success')

    # tests are run on alphabetic sorting so this must be last call
    def test_zzlogout(self):
        self.assertEqual(fgt.logout(), None)
    
if __name__ == '__main__':
    #in case it was not closed properly before
    child.expect('Escape character')
    child.sendline('\r\r')
    child.expect('.* login:')
    child.sendline( "admin\r")
    child.expect("Password:")
    child.send(conf["sut"]["passwd"]+"\n")
    child.sendline("\r")
    child.expect(' #')
    child.send('get system status\r')
    #must have expect for before /afte to be populated
    child.expect(['License','FortiOS '])
    print("after:"+child.after)
    print("after:"+child.after)
#    for i in range(0, 24):
    print(child.readline(-1))
    #incase want to reset the fortigate first
    #child.sendline(' execute factoryreset keepvmlicense')
    # must use pexepct to reset VM to factory
    #print(child.before) to get the ouput
    unittest.main()

