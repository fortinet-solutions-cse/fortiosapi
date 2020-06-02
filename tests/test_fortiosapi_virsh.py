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
import logging
import os
import re
import time
import unittest

import oyaml as yaml
import pexpect
# Disable ssl verification warnings (be responsible)
import urllib3
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortiosapi')
hdlr = logging.FileHandler('testfortiosapi.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)
fgt = FortiOSAPI()

virshconffile = os.getenv('VIRSH_CONF_FILE', "virsh.yaml")
conf = yaml.load(open(virshconffile, 'r'), Loader=yaml.SafeLoader)
# when python35 pexepct will be fixed#child = pexpect.spawn('virsh console '+conf["sut"]["vmname"],
# logfile=open("testfortiosapi.lo", "w"))

# child = pexpect.spawn('virsh console '+ str(conf["sut"]["vmname"]).strip(),logfile=open("child.log","w"))
# child.logfile = sys.stdout
# TODO add the option to run on a remote VM with -c qemu+ssh://
fgt.debug('on')
logpexecpt = open("virshconsole.log", "wb")
child = pexpect.spawn('virsh', ['console', str(conf["sut"]["vmname"]).strip()],
                      logfile=logpexecpt)
child.delaybeforesend = 0.3

class TestFortinetRestAPI(unittest.TestCase):

    # Note that, for Python 3 compatibility reasons, we are using spawnu and
    # importing unicode_literals (above). spawnu accepts Unicode input and
    # unicode_literals makes all string literals in this script Unicode by default.
    vdom = "root"

    def setUp(self):
        pass

    @staticmethod
    def sendtoconsole(cmds, in_output=" "):
        """
        Send config cli command through the virsh console in order to autoverify what the API calls does or
        prepare the Fortigate under test.
        :param cmds:
        :param in_output:
        :return:
        """
        # Use pexpect to interact with the console
        # check the prompt then send output
        # return True if commands sent and if output found
        # in_output parameter allow to search in the cmd output
        # if the string is available to check API call was correct for example

        # Trick: child.sendline(' execute factoryreset keepvmlicense')

        child.sendline('\r')
        # look for prompt or login

        logged = False
        while not logged:
            r = child.expect(['.* login:', '.* # ', '.* $ ', 'Escape character', 'Password:'], timeout=3)
            if r == 0:
                child.sendline(conf["sut"]["user"])
                rr = child.expect(["Password:", '.* # ', '.* $ '], timeout=3)
                if rr == 0:
                    child.sendline(conf["sut"]["passwd"])
                    child.expect(['.* # ', '.* $ '], timeout=2)
                    logged = True
                if rr in (1, 2):
                    child.sendline('\n')
                    logged = True
                if rr > 2:
                    child.sendline('end\n')
                    child.sendline('exit\n')
                    logged = False
            if r in (1, 2):
                child.sendline('\n')
                child.expect(['.* # ', '.* $ '], timeout=2)
                logged = True
            if r > 3:
                child.sendline('\n')
                logged = False
        result = True
        for line in cmds.splitlines():
            child.sendline(line + '\r')

        if in_output:
            try:
                r = child.expect([in_output], timeout=2)
            except:
                r = 99
                result = False
            if r != 0:
                result = False
        return result, child.readline()


    def test_00login(self):
        """
        Login to the Fortigate under test.
        User/password or API TOKEN are in config file virsh.yaml
        Can be changed by environment variable VIRSH_CONF_FILE
        If API TOKEN is present in the test conf file then we do API login
        If not do user/password
        :return:
            Success/Failure this is a unit test
        """
        if conf["sut"]["ssl"] == "yes":
            fgt.https('on')
        else:
            fgt.https(status='off')
        try:
            verify = conf["sut"]["verify"]
        except KeyError:
            verify = False

        try:
            fgt.cert = (conf["sut"]["clientcert"], conf["sut"]["clientkey"])
            fgt._session.cert = fgt.cert
        except KeyError:
            fgt.cert = None
            fgt._session.cert = None
        # ensure no previous session was left open

        try:
            apikey = conf["sut"]["api-key"]
            self.assertEqual(fgt.tokenlogin(conf["sut"]["ip"], apikey, verify=verify, vdom=conf["sut"]["vdom"]), True)
        except KeyError:
            self.assertEqual(fgt.login(conf["sut"]["ip"], conf["sut"]["user"], conf["sut"]["passwd"], verify=verify,
                                       vdom=conf["sut"]["vdom"]),
                             True)
        except Exception as e:
            self.fail("issue in the virsh yaml definition : %s" + str(e))

    def test_01logout_login(self):
        # This test if we properly regenerate the CSRF from the cookie when not restarting the program
        # can include changing login/vdom passwd on the same session
        # Check the  license validity/force a license update and wait in license call..
        if Version(fgt.get_version()) > Version('5.6'):
            try:
                self.assertTrue(fgt.license()['results']['vm']['status'] == "vm_valid" or "vm_eval")
            except KeyError:
                time.sleep(35)
        else:
            self.assertTrue(True, "not supported before 5.6")
            time.sleep(35)
        # do a logout then login again
        # TODO a expcetion check
        self.assertEqual(fgt.logout(), None)
        self.test_00login()

    def test_setaccessperm(self):
        data = {
            "name": conf["sut"]["porta"],
            "allowaccess": "ping https ssh http fgfm snmp",
            "vdom": conf["sut"]["vdom"]
        }
        # works on both multi and mono vdom
        self.assertEqual(fgt.set('system', 'interface', vdom=conf["sut"]["vdom"], data=data)['http_status'], 200)

    #        self.assertEqual(fgt.set('system', 'interface', vdom="global", data=data)['http_status'], 200)

    def test_check_version(self):
        self.assertEqual("v"+conf["sut"]["version"],fgt.get_version())

    def test_setfirewalladdress(self):
        data = {
            "name": "all.acme.test",
            "wildcard-fqdn": "*.acme.test",
            "type": "wildcard-fqdn",
        }
        # ensure the all.acme.test address is not defined
        cmds = '''config firewall address
        delete all.acme.test
        end
        '''
        self.sendtoconsole(cmds)
        self.assertEqual(fgt.set('firewall', 'address', data=data, vdom=conf["sut"]["vdom"])['http_status'], 200)
        # doing it a second time to test put instead of post
        self.assertEqual(fgt.set('firewall', 'address', data=data, vdom=conf["sut"]["vdom"])['http_status'], 200)


    def test_posttorouter(self):
        data = {
            "seq-num": "8",
            "dst": "10.11.32.0/24",
            "device": conf["sut"]["porta"],
            "gateway": "192.168.40.252",
        }
        # ensure the seq 8 for route is not present cmd will be ignored
        # assume that if vdom is root then multi-vdom is not activated.
        if  conf["sut"]["vdom"] =="root":
            cmds = '''
            config router static
            delete 8
            end
            '''
        else:
            cmds = '''
            config vdom
            edit ''' + conf["sut"]["vdom"] + '''
                config router static
                delete 8
                end
            end'''
        self.sendtoconsole(cmds)
        self.assertEqual(fgt.post('router', 'static', data=data, vdom=conf["sut"]["vdom"])['http_status'], 200)
        # vdom cmds will be ignored on non vdom
        cmds = '''config vdom
        edit ''' + conf["sut"]["vdom"] + '''
        
        show router static 8'''
        res = self.sendtoconsole(cmds, in_output="192.168.40.252")
        self.assertTrue(res, "Found the route destination in the console output")
        self.assertEqual(fgt.set('router', 'static', data, vdom=conf["sut"]["vdom"])['http_status'], 200)

    # test which must return an error (500)
    def test_accesspermfail(self):
        data = {
            "name": conf["sut"]["porta"],
            "allowaccess": "ping https ssh http fgfm snmp",
            "vdom": conf["sut"]["vdom"]
        }
        self.assertEqual(fgt.set('system', 'interface', vdom=conf["sut"]["vdom"], mkey='bad', data=data)['http_status'],
                         500,
                         "broken")

    def test_02getsystemglobal(self):
        resp = fgt.get('system', 'global', vdom="global")
        fortiversion = resp['version']
        self.assertEqual(resp['status'], 'success')
        self.assertIsNotNone(fortiversion, msg=fortiversion)

    @unittest.skipIf(conf["sut"]["vdom"] != "root",
                     "not allowed for non admin vdom")
    @unittest.skipIf(Version(conf["sut"]["version"]) < Version('6.0'), "not supported before 6.0")
    def test_is_license_valid(self):
        self.assertTrue(fgt.license()['results']['vm']['status'] == "vm_valid" or "vm_eval")

    @unittest.skipIf(conf["sut"]["vdom"] != "root",
                     "not allowed for non admin vdom")
    def test_central_management_put(self):
        # This call does not have mkey test used to validate it does not blow up
        data = {
            "type": "fortimanager",
            "fmg": "10.210.67.18",
        }
        self.assertEqual(fgt.put('system', 'central-management', vdom=conf["sut"]["vdom"], data=data)['status'],
                         'success')

    def test_execute_update(self):
        # Excuting the udate now command to ensure it does post to monitor interface (not compatible prior to 5.6)
        self.assertEqual(fgt.execute('system', 'fortiguard/update', None, vdom=conf["sut"]["vdom"])['status'],
                         'success')
        self.assertEqual(fgt.execute('system', 'fortiguard', None, mkey="update", vdom=conf["sut"]["vdom"])['status'],
                         'success')

    @unittest.skipIf(Version(conf["sut"]["version"])< Version('6.0'),"not supported before 6.0")
    def test_webfilteripsv_set(self):
        # This call does not have mkey
        data = {
            "device": conf["sut"]["porta"],
            "distance": "4",
            "gateway6": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "geo-filter": ""
        }
        self.assertEqual(
            fgt.set('webfilter', 'ips-urlfilter-setting6', vdom=conf["sut"]["vdom"], data=data)['status'],
            'success')
        # doing a second time to verify set is behaving correctly (imdepotent)
        self.assertEqual(
            fgt.set('webfilter', 'ips-urlfilter-setting6', vdom=conf["sut"]["vdom"], data=data)['status'],
            'success')

    def test_monitorresources(self):
        self.assertEqual(fgt.monitor('system', 'vdom-resource', mkey='select', vdom=conf["sut"]["vdom"])['status'],
                         'success')

    @unittest.skipIf(Version(conf["sut"]["version"])< Version('6.0'),"not supported before 6.0")
    def test_downloadconfig(self):
        if conf["sut"]["vdom"] == "global":
            parameters = {'destination': 'file',
                          'scope': 'global'}
        else:
            parameters = {'destination': 'file',
                          'scope': 'vdom',
                          'vdom': conf["sut"]["vdom"]}
        self.assertEqual(
            fgt.download('system/config', 'backup', vdom=conf["sut"]["vdom"], parameters=parameters).status_code,
            200)

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

        yamltree = yaml.load(yamldata, Loader=yaml.SafeLoader)
        yamltree['firewall']['policy'][67]['srcintf'] = [{'name': conf["sut"]["porta"]}]
        yamltree['firewall']['policy'][67]['dstintf'] = [{'name': conf["sut"]["portb"]}]


        self.assertTrue(fgt.setoverlayconfig(yamltree, vdom=conf['sut']['vdom']), True)

    def test_movecommand(self):
        data = {
            "policyid": "1",
            "name": "first",
            "action": "accept",
            "srcintf": [{"name": conf["sut"]["porta"]}],
            "dstintf": [{"name": conf["sut"]["porta"]}],
            "srcaddr": [{"name": "all"}],
            "dstaddr": [{"name": "all"}],
            "service": [{"name": "HTTPS"}],
            "schedule": "always",
            "logtraffic": "all"
        }

        fgt.delete('firewall', 'policy', vdom=conf["sut"]["vdom"], data=data)
        self.assertEqual(fgt.set('firewall', 'policy', vdom=conf["sut"]["vdom"], data=data)['status'], 'success')

        data = {
            "policyid": "2",
            "name": "second",
            "action": "accept",
            "srcintf": [{"name": conf["sut"]["porta"]}],
            "dstintf": [{"name": conf["sut"]["porta"]}],
            "srcaddr": [{"name": "all"}],
            "dstaddr": [{"name": "all"}],
            "service": [{"name": "HTTPS"}],
            "schedule": "always",
            "logtraffic": "all"
        }

        fgt.delete('firewall', 'policy', vdom=conf["sut"]["vdom"], data=data)
        self.assertEqual(fgt.set('firewall', 'policy', vdom=conf["sut"]["vdom"], data=data)['status'], 'success')

        results = (fgt.get('firewall', 'policy', vdom=conf["sut"]["vdom"]))

        self.assertIsNotNone(re.search(".*first.*second.*", str(results['results'])))
        self.assertIsNone(re.search(".*second.*first.*", str(results['results'])))

        self.assertEqual(
            fgt.move('firewall', 'policy', vdom=conf["sut"]["vdom"], mkey="1", where="after", reference_key="2")[
                'status'], 'success')

        results = (fgt.get('firewall', 'policy', vdom=conf["sut"]["vdom"]))
        self.assertIsNotNone(re.search(".*second.*first.*", str(results['results'])))
        self.assertIsNone(re.search(".*first.*second.*", str(results['results'])))

    # tests are run on alphabetic sorting so this must be last call
    def test_zzlogout(self):
        # close the console session too
        self.sendtoconsole("exit")
        child.close()
        logpexecpt.close()  # avoid py35 warning
        self.assertEqual(fgt.logout(), None)


if __name__ == '__main__':
    unittest.main()
