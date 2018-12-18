#!/usr/bin/env python
import logging
import os
import pexpect
import unittest

import oyaml as yaml
from packaging.version import Version

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
formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortiosapi')
hdlr = logging.FileHandler('testfortiosapi.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

fgt = FortiOSAPI()

virshconffile = os.getenv('VIRSH_CONF_FILE', "virsh.yaml")
conf = yaml.load(open(virshconffile, 'r'))
# when python35 pexepct will be fixed#child = pexpect.spawn('virsh console '+conf["sut"]["vmname"],
# logfile=open("testfortiosapi.lo", "w"))

# child = pexpect.spawn('virsh console '+ str(conf["sut"]["vmname"]).strip(),logfile=open("child.log","w"))
# child.logfile = sys.stdout
# TODO add the option to run on a remote VM with -c qemu+ssh://
fgt.debug('on')
logpexecpt = open("child.log", "wb")
child = pexpect.spawn('virsh', ['console', str(conf["sut"]["vmname"]).strip()],
                      logfile=logpexecpt)


class TestFortinetRestAPI(unittest.TestCase):

    # Note that, for Python 3 compatibility reasons, we are using spawnu and
    # importing unicode_literals (above). spawnu accepts Unicode input and
    # unicode_literals makes all string literals in this script Unicode by default.

    def setUp(self):
        pass

    @staticmethod
    def sendtoconsole(cmds, in_output=" "):
        # Use pexpect to interact with the console
        # check the prompt then send output
        # return True if commands sent and if output found
        # in_output parameter allow to search in the cmd output
        # if the string is available to check API call was correct for example

        # Trick: child.sendline(' execute factoryreset keepvmlicense')

        # sometime lock waiting for prompt
        child.sendline('\r')
        # look for prompt or login
        logged = False
        while not logged:
            r = child.expect(['.* login:', '#', 'Escape character'])
            if r == 0:
                child.send("admin\n")
                child.expect("Password:")
                child.send(conf["sut"]["passwd"] + "\n")
                child.expect(' #')
                logged = True
            if r == 1:
                child.sendline('\r')
                logged = True
            if r == 2:
                child.sendline('\r')
        result = True
        for line in cmds.splitlines():
            child.sendline(line + '\r')

        if in_output:
            try:
                r = child.expect([in_output], timeout=4)
            except:
                r = 99
                result = False
                pass
            if r != 0:
                result = False
        return result

    def test_00login(self):
        # adapt if using eval license or not
        if conf["sut"]["ssl"] == "yes":
            fgt.https('on')
        else:
            fgt.https(status='off')
        try:
            verify = conf["sut"]["verify"]
        except KeyError:
            verify = False
        try:
            clientcert = conf["sut"]["clientcert"]
            clientkey = conf["sut"]["clientkey"]
        except KeyError:
            clientcert=None
            clientkey=None

        try:
            apikey = conf["sut"]["api-key"]
        except KeyError:
            apikey = None

        if apikey:
            self.assertEqual(fgt.tokenlogin(conf["sut"]["ip"],apikey, vdom=conf["sut"]["vdom"], verify=verify, cert=(clientcert,clientkey)),
                             True)
        else:
            self.assertEqual(fgt.login(conf["sut"]["ip"], conf["sut"]["user"], conf["sut"]["passwd"], verify=verify,cert=(clientcert,clientkey)),
                             True)
#        except Exception as e:
#            #api-key is present but failed trying cert auth)
#            self.assertEqual(fgt.login(conf["sut"]["ip"], verify=verify,cert=(clientcert, clientkey)),True)

    def test_01logout_login(self):
        # This test if we properly regenerate the CSRF from the cookie when not restarting the program
        # can include changing login/vdom passwd on the same session
        self.assertEqual(fgt.logout(), None)
        self.test_00login()

    def test_setaccessperm(self):
        data = {
            "name": "port1",
            "allowaccess": "ping https ssh http fgfm snmp",
            "vdom": "root"
        }
        # works on both multi and mono vdom
        self.assertEqual(fgt.set('system', 'interface', vdom="root", data=data)['http_status'], 200)
        self.assertEqual(fgt.set('system', 'interface', vdom="global", data=data)['http_status'], 200)

    def test_setfirewalladdress(self):
        data = {
            "name": "all.acme.test",
            "wildcard-fqdn": "*.acme.test",
            "type": "wildcard-fqdn",
        }
        # ensure the seq 8 for route is not present
        cmds = '''config firewall address
        delete all.acme.test
        end '''
        self.sendtoconsole(cmds)
        self.assertEqual(fgt.set('firewall', 'address', data=data, vdom="root")['http_status'], 200)
        # doing it a second time to test put instead of post
        self.assertEqual(fgt.set('firewall', 'address', data=data, vdom="root")['http_status'], 200)

    def test_posttorouter(self):
        data = {
            "seq-num": "8",
            "dst": "10.11.32.0/24",
            "device": "port1",
            "gateway": "192.168.40.252",
        }
        # ensure the seq 8 for route is not present cmd will be ignored on non vdom
        cmds = '''end
        config vdom
        edit root
        config router static
        delete 8
        end
        end'''
        self.sendtoconsole(cmds)
        self.assertEqual(fgt.post('router', 'static', data=data, vdom="root")['http_status'], 200)
        # vdom cmds will be ignored on non vdom
        cmds = '''config vdom
        edit root
        show router static 8'''
        res = self.sendtoconsole(cmds, in_output="192.168.40.252")
        self.assertTrue(res)
        self.assertEqual(fgt.set('router', 'static', data, vdom="root")['http_status'], 200)

    @unittest.expectedFailure
    def test_accesspermfail(self):
        data = {
            "name": "port1",
            "allowaccess": "ping https ssh http fgfm snmp",
            "vdom": "root"
        }
        self.assertEqual(fgt.set('system', 'interface', vdom="root", mkey='bad', data=data)['http_status'], 200,
                         "broken")

    def test_02getsystemglobal(self):
        resp = fgt.get('system', 'global', vdom="global")
        fortiversion = resp['version']
        self.assertEqual(resp['status'], 'success')
        self.assertIsNotNone(fortiversion, msg=fortiversion)

    # should put a test on version to disable if less than 5.6 don't work decoration
    # @unittest.skipIf(Version(fgt.get_version()) < Version('5.6'),
    #                 "not supported with fortios before 5.6")
    def test_is_license_valid(self):
        if Version(fgt.get_version()) > Version('5.6'):
            self.assertTrue(fgt.license()['results']['vm']['status'] == "vm_valid" or "vm_eval")
        else:
            self.assertTrue(True, "not supported before 5.6")

    def test_central_management(self):
        # This call does not have mkey test used to validate it does not blow up
        data = {
            "type": "fortimanager",
            "fmg": "10.210.67.18",
        }
        self.assertEqual(fgt.put('system', 'central-management', vdom="root", data=data)['status'], 'success')

    def test_monitorresources(self):
        self.assertEqual(fgt.monitor('system', 'vdom-resource', mkey='select', vdom="root")['status'], 'success')

    def test_downloadconfig(self):
        parameters = {'destination': 'file',
                      'scope': 'global'}
        self.assertEqual(fgt.download('system/config', 'backup', vdom="root", parameters=parameters).status_code, 200)

    def test_setoverlayconfig(self):
        yamldata = '''
            antivirus:
              profile:
                apisettree:
                  "scan-mode": "quick"
                  'http': {"options": "scan avmonitor",}
                  "emulator": "enable"
            firewall:
              policy:
                67:
                  'name': "Testfortiosapi"
                  'action': "accept"
                  'srcintf': [{"name": "port1"}]
                  'dstintf': [{"name": "port2"}]
                  'srcaddr': [{"name": "all"}]
                  'dstaddr': [{"name": "all"}]
                  'schedule': "always"
                  'service': [{"name": "HTTPS"}]
                  "utm-status": "enable"
                  "profile-type": "single"
                  'av-profile': "apisettree"
                  'profile-protocol-options': "default"
                  'ssl-ssh-profile': "certificate-inspection"
                  'logtraffic': "all"
                    '''
        #        yamltree=OrderedDict()
        yamltree = yaml.load(yamldata)
        self.assertTrue(fgt.setoverlayconfig(yamltree, vdom=conf['sut']['vdom']), True)

    # tests are run on alphabetic sorting so this must be last call
    def test_zzlogout(self):
        child.terminate()
        logpexecpt.close()  # avoid py35 warning
        self.assertEqual(fgt.logout(), None)


if __name__ == '__main__':
    unittest.main()
