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
# fortiosapi.py aims at simplyfing the configuration and
# integration of Fortgate configuration using the restapi
#
# A Python module to abstract configuration using FortiOS REST API
#
###################################################################

import time
import paramiko
import subprocess
import requests
from collections import namedtuple
import json
import pprint
# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
from argparse import Namespace
# Disable warnings about certificates.
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
# may need to move to specifying the ca or use Verify=false
# cafile = 'cacert.pem'
# r = requests.get(url, verify=cafile)
logging.getLogger(__name__).addHandler(NullHandler())
# create logger
LOG = logging.getLogger('fortiosapi')


class FortiOSAPI(object):
    def __init__(self):
        self._https = True
        self._fortiversion = "Version is set when logged"
        # reference the fortinet version of the targeted product.
        self._session = requests.session()  # use single session
        # persistant and same for all
        self._session.verify = False
        # (can be changed to) self._session.verify = '/path/to/certfile'

    def logging(self, response):
        try:
            LOG.debug("Request : %s on url : %s  ", response.request.method,
                      response.request.url)
            LOG.debug("Response : http code %s  reason : %s  ",
                      response.status_code, response.reason)
            LOG.debug("raw response:  %s ", response.content)
        except:
            LOG.warning("method errors in request when global")

    def debug(self, status):
        if status == 'on':
            LOG.setLevel(logging.DEBUG)

    def formatresponse(self, res, vdom=None):
        LOG.debug("formating response")
        self.logging(res)
        # Generic way to format the return from FortiAPI
        # If vdom is global the resp is a dict of resp (even 1)
        # 1 per vdom we check only the first one here (might need a more
        # complex check)
        if vdom == "global":
            resp = json.loads(res.content.decode('utf-8'))[0]
            resp['vdom'] = "global"
        else:
            LOG.debug("content res: %s", res.content)
            resp = json.loads(res.content.decode('utf-8'))
        return resp

    def https(self, status):
        if status == 'on':
            self._https = True
        if status == 'off':
            self._https = False

    def update_cookie(self):
        # Retrieve server csrf and update session's headers
        LOG.debug("cookies are  : %s ", self._session.cookies )
        for cookie in self._session.cookies:
            if cookie.name == 'ccsrftoken':
                csrftoken = cookie.value[1:-1]  # token stored as a list
                LOG.debug("csrftoken before update  : %s ", csrftoken)
                self._session.headers.update({'X-CSRFTOKEN': csrftoken})
                LOG.debug("csrftoken after update  : %s ", csrftoken)

    def login(self, host, username, password):
        self.host = host
        if self._https is True:
            self.url_prefix = 'https://' + self.host
        else:
            self.url_prefix = 'http://' + self.host
        url = self.url_prefix + '/logincheck'
        res = self._session.post(
            url,
            data='username=' + username + '&secretkey=' + password + "&ajax=1")
        self.logging(res)
        # Ajax=1 documented in 5.6 API ref but available on 5.4
        if b"1document.location=\"/ng/prompt?viewOnly&redir" in res.content:
            # Update session's csrftoken
            self.update_cookie()
        else:
            raise Exception('login failed')
        try:
            self._fortiversion = self.get('system', 'status',vdom="root")['version']
        except:
            raise Exception('can not get following login')
            
    def get_version(self):
        return self._fortiversion

    def get_mkey(self, path, name, vdom=None, data=None):
        # retreive the table mkey from schema
        schema = self.schema(path, name, vdom=None)
        try:
            keyname = schema['mkey']
        except KeyError:
            LOG.warning("there is no mkey for %s/%s", path, name)
            return None
        try:
            mkey = data[keyname]
        except KeyError:
            LOG.warning("mkey %s not set in the data", mkey)
            return None
        return mkey

    def logout(self):
        url = self.url_prefix + '/logout'
        res = self._session.post(url)
        self._session.close()
        self._session.cookies.clear()
        self.logging(res)

    def cmdb_url(self, path, name, vdom, mkey=None):
        # return builded URL
        url_postfix = '/api/v2/cmdb/' + path + '/' + name
        if mkey:
            url_postfix = url_postfix + '/' + str(mkey)
        if vdom:
            LOG.debug("vdom is: %s", vdom)
            if vdom == "global":
                url_postfix += '?global=1'
            else:
                url_postfix += '?vdom=' + vdom
        url = self.url_prefix + url_postfix
        LOG.debug("urlbuild is %s with crsf: %s", url ,self._session.headers )
        return url

    def mon_url(self, path, name, vdom=None, mkey=None):
        # return builded URL
        url_postfix = '/api/v2/monitor/' + path + '/' + name
        if mkey:
            url_postfix = url_postfix + '/' + str(mkey)
        if vdom:
            LOG.debug("vdom is: %s", vdom)
            if vdom == "global":
                url_postfix += '?global=1'
            else:
                url_postfix += '?vdom=' + vdom

        url = self.url_prefix + url_postfix
        return url

    def monitor(self, path, name, vdom=None, mkey=None, parameters=None):
        url = self.mon_url(path, name, vdom, mkey)
        res = self._session.get(url, params=parameters)
        LOG.debug("in MONITOR function")
        return self.formatresponse(res, vdom=vdom)

    def download(self, path, name, vdom=None, mkey=None, parameters=None):
        url = self.mon_url(path, name)
        res = self._session.get(url, params=parameters)
        LOG.debug("in DOWNLOAD function")
        return res
       
    def upload(self, path, name, vdom=None, mkey=None, parameters=None, data=None, files=None):
        url = self.mon_url(path, name)
        res = self._session.post(url, params=parameters, data=data, files=files)
        LOG.debug("in UPLOAD function")
        return res
               
    def get(self, path, name, vdom=None, mkey=None, parameters=None):
        url = self.cmdb_url(path, name, vdom, mkey)

        res = self._session.get(url, params=parameters)
        LOG.debug("in GET function")
        return self.formatresponse(res, vdom=vdom)

    def schema(self, path, name, vdom=None):
        # vdom or global is managed in cmdb_url
        if vdom is None:
            url = self.cmdb_url(path, name, vdom) + "?action=schema"
        else:
            url = self.cmdb_url(path, name, vdom) + "&action=schema"

        res = self._session.get(url)
        self.logging(res)
        if res.status_code is 200:
            return json.loads(res.content.decode('utf-8'))['results']
        else:
            return json.loads(res.content.decode('utf-8'))

    def get_name_path_dict(self, vdom=None):
        # return builded URL
        url_postfix = '/api/v2/cmdb/'
        if vdom is None:
            url_postfix += '?vdom=' + vdom + "&action=schema"
        else:
            url_postfix += "?action=schema"

        url = self.url_prefix + url_postfix
        cmdbschema = self._session.get(url)
        self.logging(cmdbschema)
        j = json.loads(cmdbschema.content.decode('utf-8'))['results']
        dict = []
        for keys in j:
            if "__tree__" not in keys['path']:
                dict.append(keys['path'] + " " + keys['name'])
        return dict

    def post(self, path, name, vdom=None,
             mkey=None, parameters=None, data=None):
        if not mkey:
            mkey = self.get_mkey(path, name, vdom=vdom, data=data)
        #post with mkey will return a 404 as the next level is not there yet
        url = self.cmdb_url(path, name, vdom, mkey=None)
        res = self._session.post(
            url, params=parameters, data=json.dumps(data))

        LOG.debug("in POST function")
        return self.formatresponse(res, vdom=vdom)

    def put(self, path, name, vdom=None,
            mkey=None, parameters=None, data=None):
        if not mkey:
            mkey = self.get_mkey(path, name, vdom=vdom, data=data)
        url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.put(url, params=parameters,
                                data=json.dumps(data))
        LOG.debug("in PUT function")
        return self.formatresponse(res, vdom=vdom)

    def delete(self, path, name, vdom=None,
               mkey=None, parameters=None, data=None):
        # Need to find the type of the mkey to avoid error when integer assume
        # the other types will be ok.
        if not mkey:
            mkey = self.get_mkey(path, name, vdom=vdom, data=data)
        url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.delete(
            url, params=parameters, data=json.dumps(data))

        LOG.debug("in DELETE function")
        return self.formatresponse(res, vdom=vdom)

# Set will try to post if err code is 424 will try put (ressource exists)
# may add a force option to delete and redo if troubles.
    def set(self, path, name, vdom=None,
            mkey=None, parameters=None, data=None):
        #post with mkey will return a 404 as the next level is not there yet
        url = self.cmdb_url(path, name, vdom, mkey=None)
        res = self._session.post(url, params=parameters, data=json.dumps(data))
        LOG.debug("in SET function after POST")
        r = self.formatresponse(res, vdom=vdom)

        if r['http_status'] == 424 or r['http_status'] == 405:
            LOG.warning(
                "Try to post on %s  failed doing a put to force parameters\
                change consider delete if still fails ",
                res.request.url)
            if not mkey:
                mkey = self.get_mkey(path, name, vdom=vdom, data=data)
            url = self.cmdb_url(path, name, mkey=mkey, vdom=vdom)
            res = self._session.put(
                url, params=parameters, data=json.dumps(data))
            LOG.debug("in SET function after PUT")
            return self.formatresponse(res, vdom=vdom)
        else:
            return r

# send multiline string ''' get system status ''' using ssh
    def ssh(self, cmds, host, user, password=None):
        ''' Send a multi line string via ssh to the fortigate '''
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=22, username=user, password=password,
                       allow_agent=False, timeout=10)
        LOG.debug("ssh login to  %s ", host)
        # commands is a multiline string using the ''' string ''' format
        try:
            stdin, stdout, stderr = client.exec_command(cmds)
        except:
            LOG.debug("exec_command failed")
            raise subprocess.CalledProcessError(returncode=retcode, cmd=cmds,
                                                output=output)
            
        LOG.debug("ssh command in:  %s out: %s err: %s ", stdin, stdout , stderr)
        retcode = stdout.channel.recv_exit_status()
        LOG.debug("Paramiko return code : %s ", retcode)
        client.close()  # @TODO re-use connections
        if retcode > 0:
            output = stderr.read().strip()
            raise subprocess.CalledProcessError(returncode=retcode, cmd=cmds,
                                                output=output)
        results = stdout.read()
        LOG.debug("ssh cmd %s | out: %s | err: %s ", cmds, results, retcode)
        # fortigate ssh send errors on stdout so checking that
        if "Command fail. Return code" in str(results):
            # TODO fill retcode with the output of the FGT
            raise subprocess.CalledProcessError(returncode=retcode, cmd=cmds,
                                                output=results)
        return (''.join(str(results)), ''.join(str(stderr)))

    def license(self):
        resp = self.monitor('license', 'status')
        if resp['results']['vm']['status'] == "vm_valid":
            return resp
        else:
            # if vm license not valid we try to update and check again
            url = self.mon_url('system', 'fortiguard', mkey='update')
            postres = self._session.post(url)
            LOG.debug("Return POST fortiguard %s:", postres)
            postresp = json.loads(postres.content.decode('utf-8'))
            if postresp['status'] == 'success':
                time.sleep(17)
                return self.monitor('license', 'status')


# Todo for license check and update
# GET /api/v2/monitor/license/status
# To update FortiGuard license status, you can use the following API
# POST api/v2/monitor/system/fortiguard/update
