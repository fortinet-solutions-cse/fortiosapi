#!/usr/bin/python

from fortigateconf import FortiOSConf
import sys
import json
import pprint
import json
from argparse import Namespace
import logging
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortinetconflib')
hdlr = logging.FileHandler('/var/tmp/testapi.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)

logger.debug('often makes a very good meal of %s', 'visiting tourists')

fgt = FortiOSConf()

def json2obj(data):
    return json.loads(data, object_hook=lambda d: Namespace(**d))


def main():
    # Login to the FGT ip
    fgt.debug('on')
    fgt.login('10.210.8.4','admin','')
    pp = pprint.PrettyPrinter(indent=4)
    fortiport = "port5"
    cp = {
        "ip_address": "10.10.11.254"
    }
    pp.pprint(cp)
   
    data = {
        "name": fortiport,
        "interface": fortiport,
        "mode": "static",
        "ip": " "+cp['ip_address']+" 255.255.255.0",
        "allowaccess":"ping",
        "vdom":"root"
    }
    resp = fgt.set('system','interface', vdom="root", data=data)


    fgt.logout()


if __name__ == '__main__':
  main()
