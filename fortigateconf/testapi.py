#!/usr/bin/python

from fortigateconf import FortiOSConf
import sys
import json
import pprint
import json
from argparse import Namespace
import logging

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.WARNING)

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
           "seq-num" :"7",
           "dst": "10.10.30.0 255.255.255.0",
           "device": "port2",
           "gateway": "192.168.40.254",
        }
    pp = pprint.PrettyPrinter(indent=4)
    d=json2obj(json.dumps(data))
    resp = fgt.schema('router','static')
    pp.pprint(resp)
    
    resp = fgt.post('router','static', vdom="root", data=data)
    r = json2obj(resp)
    pp.pprint(r)
    if r.http_status == 424:
        mkey = data['seq-num']
        resp = fgt.put('router','static', mkey=mkey, data=data)
        pp.pprint(json.loads(resp))

    pp.pprint(json.loads(resp))
   
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
