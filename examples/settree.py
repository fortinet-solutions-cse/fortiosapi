#!/usr/bin/env python
# License upload using FORTIOSAPI from Github

import logging
import sys

# oyaml preserve order which can be important for Fortinet config.
# we want to make it simple for the user
from fortiosapi import FortiOSAPI

formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortiosapi')
hdlr = logging.FileHandler('testfortiosapi.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)


def main():
    # Parse for command line argument for fgt ip
    if len(sys.argv) < 2:
        # Requires fgt ip and password
        print "Please specify fgt ip address"
        exit()

    # Initilize fgt connection
    ip = sys.argv[1]
    try:
        passwd = sys.argv[2]
    except:
        passwd = ''
    # fgt = FGT(ip)

    # Hard coded vdom value for all requests
    vdom = "root"

    # Login to the FGT ip

    fgt = FortiOSAPI()

    fgt.login(ip, 'admin', passwd)
    yamldata = '''
        antivirus:
            profile:
                apiset:
                    'name': "apiset"
                    "scan-mode": "quick"
                    'http': {"options": "scan avmonitor",}
                    "emulator": "enable"
        firewall:
            policy:
                66:
                  'name': "Testfortiosapi",
                  'action': "accept",
                  'srcintf': [{"name": "port1"}],
                  'dstintf': [{"name": "port2"}],
                  'srcaddr': [{"name": "all"}],
                  'dstaddr': [{"name": "all"}],
                  'schedule': "always",
                  'service': [{"name": "HTTPS"}],
                  "utm-status": "enable",
                  "profile-type": "single",
                  'av-profile': "apiset",
                  'profile-protocol-options': "default",
                  'ssl-ssh-profile': "certificate-inspection",
                  'logtraffic': "all"
                '''

    fgt.settree(yamltree=yamldata)
    fgt.logout()


if __name__ == '__main__':
    main()
