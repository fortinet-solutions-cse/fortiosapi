#!/usr/bin/env python
#License upload using FORTIOSAPI from Github

import sys
from fortiosapi import FortiOSAPI
import json

def main():

    # Parse for command line argument for fgt ip
    if len(sys.argv) < 2:
        # Requires fgt ip and vdom
        print "Please specify fgt ip address"
        exit()

    # Initilize fgt connection
    ip = sys.argv[1]
    #fgt = FGT(ip)

    # Hard coded vdom value for all requests
    vdom = "root"

    # Login to the FGT ip

    fgt = FortiOSAPI()

    fgt.login(ip,'admin','')
    parameters = { 'global':'1' }
    upload_data={'source':'upload',
                 'scope':'global'}
    files={'file': ('license',open("license.lic", 'r'), 'text/plain')}
	
    fgt.upload('system/vmlicense','upload',
            data=upload_data,
            parameters=parameters,
            files=files)


    fgt.logout()

if __name__ == '__main__':
  main()