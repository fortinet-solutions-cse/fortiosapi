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
    resp = fgt.get('router','static', vdom="root", mkey=8)
    pp.pprint(resp)
    
    resp = fgt.delete('router','static', vdom="root", data=data)
    
    pp.pprint(resp['reason'])

   
    # Sample API calls
    #fgt.get_v1('monitor', 'firewall', 'policy')
    #fgt.get_v1('cmdb', 'firewall', 'address')
    #resp = fgt.get('monitor', 'firewall', 'policy')
    #jresp = json.loads(resp)
    #pp.pprint(jresp)
    #print "STATUS:"+jresp["status"]

#    fgt.get('monitor', 'firewall', 'session')
#    fgt.get('monitor', 'firewall', 'session', parameters={'ip_version':'ipv4',
#                                                          'count':2})

    #fgt.get('monitor', 'fortiview', 'statistics')
#    fgt.get('monitor', 'fortiview', 'statistics', parameters={'realime':True})
#    fgt.get('monitor', 'fortiview', 'statistics', parameters={'realime':False})


#                                                              'before':2})
#    fgt.delete('cmdb', 'firewall', 'policy', mkey=1)
#    fgt.delete('cmdb', 'firewall', 'policy')

    # Always logout after session is done
    fgt.logout()


if __name__ == '__main__':
  main()
