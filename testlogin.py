#!/usr/bin/python
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


def main():
    # Login to the FGT ip
    fgt.debug('on')
    fgthost = '192.168.115.131'
    user = 'admin'
    passwd = ''
    resp = fgt.login(fgthost, user, passwd)
    pp = pprint.PrettyPrinter(indent=4)
    resp = fgt.license()
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(resp)

if __name__ == '__main__':
    main()
