#!/usr/bin/python

from fortiosapi import FortiOSConf
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

fos = FortiOSConf()

def json2obj(data):
    return json.loads(data, object_hook=lambda d: Namespace(**d))


def main():
    # Login to the FGT ip
    fos.debug('on')
    fos.login('10.10.10.24','admin','')
    pp = pprint.PrettyPrinter(indent=4)
    fortiport = "port2"
    cp = {
        "ip_address": "10.10.11.254"
    }
    pp.pprint(cp)
   
    data = {
        "policyid":3,
        "name":"3",
#        "action":"deny",
        "srcintf": "port1",
        "dstintf":"port2",
        "srcaddr":"all",
        "dstaddr":"all",
        "service":"HTTPS",
        "logtraffic":"all",
        "schedule":'always',
        "logtraffic":"all",
        "status":"enable",
    }

    datalist = {
        "policyid":"3",
        "name":"3",
#        "action":"accept",
        "srcintf": [{"name":"port1"}],
        "dstintf":[{"name":"port2"}],
        "srcaddr":[{"name":"all"}],
        "dstaddr":[{"name":"all"}],
        "service":[{"name":"HTTPS"}],
        "logtraffic":"all",
        "schedule":'always',
        "logtraffic":"all",
         "status":"enable",       
    }



    resp = fos.set('firewall','policy',data=datalist)

    data = {
        #         "action" : "add",
        "seq-num" :"8",
        "dst": "10.10.30.0 255.255.255.0",
        "device": "port2",
        "gateway": "192.168.40.254",
    }
    pp = pprint.PrettyPrinter(indent=4)
    
    d=json2obj(json.dumps(data))
#    resp = fos.set('router','static', vdom="root", data=data)
        
    pp.pprint(resp['reason'])

    
    # Sample API calls
    #fos.get_v1('monitor', 'firewall', 'policy')
    #fos.get_v1('cmdb', 'firewall', 'address')
    #resp = fos.get('monitor', 'firewall', 'policy')
    #jresp = json.loads(resp)
    #pp.pprint(jresp)
    #print "STATUS:"+jresp["status"]

#    fos.get('monitor', 'firewall', 'session')
#    fos.get('monitor', 'firewall', 'session', parameters={'ip_version':'ipv4',
#                                                          'count':2})

    #fos.get('monitor', 'fortiview', 'statistics')
#    fos.get('monitor', 'fortiview', 'statistics', parameters={'realime':True})
#    fos.get('monitor', 'fortiview', 'statistics', parameters={'realime':False})


#                                                              'before':2})
#    fos.delete('cmdb', 'firewall', 'policy', mkey=1)
#    fos.delete('cmdb', 'firewall', 'policy')

    # Always logout after session is done
    fos.logout()


if __name__ == '__main__':
  main()
