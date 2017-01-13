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

###################################################################
#
# fortigateconf.py aims at simplyfing the configuration and 
# integration of Fortgate configuration using the restapi
#
# A Python module to abstract configuration using FortiOS REST API 
#
###################################################################
import paramiko
import subprocess
import requests
from collections import namedtuple
#Disable warnings about certificates.
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import json
# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
# create logger
LOG = logging.getLogger('fortinetconflib')

from argparse import Namespace
def json2obj(data):
    return json.loads(data.decode('utf-8'), object_hook=lambda d: Namespace(**d))

class FortiOSConf(object):
    def __init__(self):
        self._https = True
        self._session = requests.session() # use single session

    def logging(self, response):
        LOG.debug("Request : %s on url : %s  ",response.request.method,
                      response.request.url) 
        LOG.debug("Response : http code %s  reason : %s  ", response.status_code,response.reason)
        
        content=response.content
        if content is not 'null':
            if content is not None:
                try:
                    j = json.loads(content)
                except (ValueError,TypeError):
                    LOG.debug("Response raw content:  %s ", content)
                else:
                    if response.status_code is 200 :
                        try:
                            result=j['results']	
                        except (KeyError,TypeError):
                            LOG.debug("Response results content:  %s ", j)
                        else:
                            LOG.debug("Response result content:  %s ", str(result))
                    else:
                        LOG.debug("Response raw content:  %s ", j)
                        
    def debug(self, status):
        if status == 'on':
          LOG.setLevel(logging.DEBUG)
      
    def https(self, status):
        if status == 'on':
          self._https = True
        if status == 'off':
          self._https = False

    def update_cookie(self):
        # Retrieve server csrf and update session's headers
        for cookie in self._session.cookies:
            if cookie.name == 'ccsrftoken':
                csrftoken = cookie.value[1:-1] # token stored as a list
                LOG.debug("csrftoken before update  : %s ", cookie) 
                self._session.headers.update({'X-CSRFTOKEN': csrftoken})
                LOG.debug("csrftoken after update  : %s ", cookie) 

    def login(self,host,username,password):
        self.host = host
        if self._https is True:
            self.url_prefix = 'https://' + self.host
        else:
            self.url_prefix = 'http://' + self.host
        url = self.url_prefix + '/logincheck'
        res = self._session.post(url,
                                data='username='+username+'&secretkey='+password,
                                verify=False)
        self.logging(res)

        # Update session's csrftoken
        self.update_cookie()

    def logout(self):
        url = self.url_prefix + '/logout'
        res = self._session.post(url,verify=False)

        self.logging(res)


    def cmdb_url(self, path, name, vdom, mkey):
      
        # return builded URL
        url_postfix = '/api/v2/cmdb/' + path + '/' + name
        if mkey:
            url_postfix = url_postfix + '/' + str(mkey)
        if vdom:
            url_postfix += '?vdom=' + vdom
            
        url = self.url_prefix + url_postfix
        return url

    def get(self, path, name, vdom=None, mkey=None, parameters=None):
        url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.get(url,params=parameters)
        # return the content but add the http method reason (give better hint what to do)
        resp = json.loads(res.content.decode('utf-8'))
        resp['reason']=res.reason
        self.logging(res)
        return resp

    def schema(self, path, name, vdom=None, mkey=None, parameters=None):
        if vdom is None:
            url = self.cmdb_url(path, name, vdom, mkey)+"?action=schema"
        else:
            url = self.cmdb_url(path, name, vdom, mkey)+"&action=schema"
             
        res = self._session.get(url,params=parameters)
        self.logging(res)
        if res.status_code is 200 :
            return json.loads(res.content.decode('utf-8'))['results']
        else:
            return json.loads(res.decode('utf-8'))

    def get_name_path_dict(self, vdom=None):
         # return builded URL
        url_postfix = '/api/v2/cmdb/'
        if vdom is None:
            url_postfix += '?vdom=' + vdom +"&action=schema"
        else:
            url_postfix +="?action=schema"

        url = self.url_prefix + url_postfix
        cmdbschema = self._session.get(url)
        self.logging(cmdbschema)
        j = json.loads(cmdbschema.content.decode('utf-8'))['results']
        dict = [ ]
        for keys in j:
            if "__tree__" not in keys['path']:
                dict.append(keys['path']+" "+keys['name'])
        return dict

    def post(self, path, name, vdom=None, mkey=None, parameters=None, data=None):
        url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.post(url,params=parameters,data=json.dumps(data),verify = False)            
        # return the content but add the http method reason (give better hint what to do)
        resp = json.loads(res.content.decode('utf-8'))
        resp['reason']=res.reason
        self.logging(res)
        return resp

    def put(self, path, name, vdom=None, mkey=None, parameters=None, data=None):
        url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.put(url,params=parameters,data=json.dumps(data),verify=False)         # return the content but add the http method reason (give better hint what to do)
        resp = json.loads(res.content.decode('utf-8'))
        resp['reason']=res.reason
        self.logging(res)
        return resp

    def delete(self, path, name, vdom=None, mkey=None, parameters=None, data=None):
        # Need to find the type of the mkey to avoid error when integer assume the other types will be ok.
        schema = self.schema(path, name)
        keytype = schema['mkey_type']
        if keytype == "integer" :
            url = self.cmdb_url(path, name, vdom, mkey)
        else:
            url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.delete(url,params=parameters,data=json.dumps(data))           
        # return the content but add the http method reason (give better hint what to do)
        resp = json.loads(res.content.decode('utf-8'))
        resp['reason']=res.reason
        self.logging(res)
        return resp
    
# Set will try to post if err code is 424 will try put (ressource exists)
#may add a force option to delete and redo if troubles.
    def set(self, path, name, vdom=None, mkey=None, parameters=None, data=None):
        url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.post(url,params=parameters,data=json.dumps(data))            
        self.logging(res)
        r = json2obj(res.content)
        if r.http_status == 424:
            LOG.warning("Try to post on %s failed doing a put to force parameters change consider delete if still fails ", res.request.url)
            #retreive the table mkey from schema
            schema = self.schema(path, name, vdom=None)
            keyname = schema['mkey']
            mkey = data[keyname]
            url = self.cmdb_url(path, name, mkey=mkey,vdom=vdom)
            res = self._session.put(url,params=parameters,data=json.dumps(data),verify=False)
            self.logging(res)
        # return the content but add the http method reason (give better hint what to do)
        resp = json.loads(res.content.decode('utf-8'))
        resp['reason']=res.reason
        self.logging(res)
        return resp


## send multiline string ''' get system status ''' using ssh
    def ssh(self,cmds, host, user, password=None):
        ''' Send a multi line string via ssh to the fortigate '''
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=22, username=user, password=password,
                       allow_agent=False,timeout=10)
        LOG.debug("ssh login to  %s ", host)
        #commands is a multiline string using the ''' string ''' format
        stdin, stdout, stderr = client.exec_command(cmds)
            
        retcode = stdout.channel.recv_exit_status()
        client.close()  # @TODO re-use connections
        if retcode > 0:
            output = stderr.read().strip()
            raise subprocess.CalledProcessError(returncode=retcode, cmd=cmds,
                                                output=output)
        results=stdout.read()
        LOG.debug("ssh cmd %s | out: %s | err: %s ", cmds,results,retcode)
        #fortigate ssh send errors on stdout so checking that 
        if "Command fail. Return code" in str(results):
            # TODO fill retcode with the output of the FGT
            raise subprocess.CalledProcessError(returncode=retcode, cmd=cmds,
                                                output=results)
        return (''.join(str(results)), ''.join(str(stderr)))
