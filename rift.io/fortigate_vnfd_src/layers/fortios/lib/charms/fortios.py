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
from charmhelpers.core.hookenv import (
    config,
    log,
)

from fortigateconf import FortiOSConf

fgt = FortiOSConf()
cfg = config()

class FoS(object):
    def __init__(self,name):
        pass
    

def set( name, path, vdom=None,data=None):
    login()
    if  cfg['vdom'] is "":
        vdom ="root"
    else:
        vdom = cfg['vdom']
        
    resp = fgt.set(name,path,vdom=vdom,data=data)
    fgt.logout()
    if resp['status'] == "success":
        return True, resp
    else:
        return False,  resp['reason']

def connectionisok( vdom=None):
    #may be less stress to create a second connection and leave it open or use monit part.
    login()
    resp = fgt.get('system','status',vdom=vdom)
    fgt.logout()
    if resp['status'] == "success":
        return True
    ## TODO Return the content of stdout.
    else:
        return False,  resp['reason']
    
def sshcmd( cmds):
    try:
        # Rift force None as a value by default need to be caught
        if cfg['password'] and cfg['password'].strip():
            out,err = fgt.ssh(cmds, cfg['hostname'],cfg['user'],password=cfg['password'])
        else:
            out,err = fgt.ssh(cmds, cfg['hostname'],cfg['user'],password="")
        return out, err
    except Exception as e:
        log(repr(e))

        


def login():
    if all(k in cfg for k in ['password', 'hostname', 'user']):
        fortigate = cfg['hostname']
        user = cfg['user']
        passwd = cfg['password']
        return fgt.login(fortigate,user,passwd)
    else:
        raise Exception
