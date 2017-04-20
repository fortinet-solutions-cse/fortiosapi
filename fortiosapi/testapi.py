#!/usr/bin/python

from fortiosapi import FortiOSAPI
import sys
import json
import pprint
import json
from argparse import Namespace
import logging
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortiosapi')
hdlr = logging.FileHandler('/var/tmp/testapi.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)

fos = FortiOSAPI()

def json2obj(data):
    return json.loads(data, object_hook=lambda d: Namespace(**d))


def main():
    # Login to the FGT ip
    fos.debug('on')
    fos.login('192.168.115.128','admin','adminpasswd')
    pp = pprint.PrettyPrinter(indent=4)
    fortiport = "port2"
    cp = {
        "ip_address": "10.10.11.254"
    }
    pp.pprint(cp)
   
    data = {
        "type": "fortimanager",
        "fmg": "10.210.67.18"
        }
        



    resp = fos.put('system','central-management',data=data,vdom='vdom')

    pp = pprint.PrettyPrinter(indent=4)         
    pp.pprint(resp)


    # Always logout after session is done
    fos.logout()


if __name__ == '__main__':
  main()
