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


if __name__ == '__main__':
  main()
