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

import copy
import json
# Set default logging handler to avoid "No handler found" warnings.
import logging
import subprocess
import time
from collections import OrderedDict

import paramiko
import requests

try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
# Disable warnings about certificates.
# from requests.packages.urllib3.exceptions import InsecureRequestWarning

# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
# may need to move to specifying the ca or use Verify=false
# verify="/etc/ssl/certs/" on Debian to use the system CAs
logging.getLogger(__name__).addHandler(NullHandler())
# create logger
LOG = logging.getLogger('fortiosapi')


class FortiOSAPI(object):
    def __init__(self):
        self.host = None
        self._https = True
        self._logged = False
        self._fortiversion = "Version is set when logged"
        # reference the fortinet version of the targeted product.
        self._session = requests.session()  # use single session
        # persistant and same for all
        self._session.verify = False
        # (can be changed to) self._session.verify = '/etc/ssl/certs/' or True
        # Will be switch to true by default it uses the python CA list in this case
        self.timeout = 120
        self.cert = None
        self._apitoken = None
        self._license = None
        self.url_prefix = None


    @staticmethod
    def logging(response):
        try:
            LOG.debug("response content type : %s", response.headers['content-type'])
            LOG.debug("Request : %s on url : %s  ", response.request.method,
                      response.request.url)
            LOG.debug("Response : http code %s  reason : %s  ",
                      response.status_code, response.reason)
            LOG.debug("raw response:  %s ", response.content)
        except:
            LOG.warning("method errors in request when global")


    @staticmethod
    def debug(status):
        if status == 'on':
            LOG.setLevel(logging.DEBUG)


    def formatresponse(self, res, vdom=None):
        LOG.debug("formating response")
        self.logging(res)
        # Generic way to format the return from FortiAPI
        # If vdom is global the resp is a dict of resp (even 1)
        # 1 per vdom we check only the first one here (might need a more
        # complex check)
        if self._license == "Invalid":
            LOG.debug("License invalid detected")
            raise Exception("unauthorized probably an invalid license")

        # try:
        #    if res['http_status'] is 401:
        #        raise Exception("http code 401 login or license invalid")
        # except KeyError:
        #    pass

        try:
            if vdom == "global":
                resp = json.loads(res.content.decode('utf-8'))[0]
                resp['vdom'] = "global"
            else:
                LOG.debug("content res: %s", res.content)
                resp = json.loads(res.content.decode('utf-8'))
            return resp
        except:
            # that means res.content does not exist (error in general)
            # in that case return raw result TODO fix that with a loop in case of global
            LOG.warning("in formatresponse res.content does not exist, should not occur")
            return res


    def check_session(self):
        if not self._logged:
            raise Exception("Not logged on a session, please login")
        if self._license == "Invalid":
            raise Exception("License invalid")


    def https(self, status):
        if status == 'on':
            self._https = True
        if status == 'off':
            self._https = False
        LOG.debug("https mode is %s", self._https)


    def update_cookie(self):
        # Retrieve server csrf and update session's headers
        LOG.debug("cookies are  : %s ", self._session.cookies)
        for cookie in self._session.cookies:
            if cookie.name == 'ccsrftoken':
                csrftoken = cookie.value[1:-1]  # token stored as a list
                LOG.debug("csrftoken before update  : %s ", csrftoken)
                self._session.headers.update({'X-CSRFTOKEN': csrftoken})
                LOG.debug("csrftoken after update  : %s ", csrftoken)
        LOG.debug("New session header is: %s", self._session.headers)


    def login(self, host, username, password, verify=False, cert=None, timeout=12):
        self.host = host
        LOG.debug("self._https is %s", self._https)
        if not self._https:
            self.url_prefix = 'http://' + self.host
        else:
            self.url_prefix = 'https://' + self.host

        url = self.url_prefix + '/logincheck'
        if not self._session:
            self._session = requests.session()
            # may happen if logout is called
        if verify is not False:
            self._session.verify = verify

        if cert is not None:
            self._session.cert = cert
        # set the default at 12 see request doc for details http://docs.python-requests.org/en/master/user/advanced/
        self.timeout = timeout

        res = self._session.post(
            url,
            data='username=' + username + '&secretkey=' + password + "&ajax=1", timeout=self.timeout)
        self.logging(res)
        # Ajax=1 documented in 5.6 API ref but available on 5.4
        LOG.debug("logincheck res : %s", res.content)
        if res.content.decode('ascii')[0] == '1':
            # Update session's csrftoken
            self.update_cookie()
            self._logged = True
            try:
                resp_lic = self.monitor('license', 'status', vdom="global")
                LOG.debug("response monitor license: %s", resp_lic)
                self._fortiversion = resp_lic['version']
                # suppose license is valid double check later
                # Proper validity is complex and different on VM or Hardware
                self._license = "Valid"
            except Exception as e:
                raise e
            if "license?viewOnly" in res.content.decode('ascii'):
                # should work with hardware and vm (content of license/status differs
                self._license = "Invalid"
            else:
                self._license = "Valid"
            return True
        else:
            self._logged = False
            raise Exception('login failed')


    def tokenlogin(self, host, apitoken, verify=False, cert=None, timeout=12):
        # if using apitoken method then login/passwd will be disabled
        self.host = host
        if not self._session:
            self._session = requests.session()
            # may happen at start or if logout is called
        self._session.headers.update({'Authorization': 'Bearer ' + apitoken})
        self._logged = True
        LOG.debug("self._https is %s", self._https)
        if not self._https:
            self.url_prefix = 'http://' + self.host
        else:
            self.url_prefix = 'https://' + self.host

        if verify is not False:
            self._session.verify = verify

        if cert is not None:
            self._session.cert = cert
        # set the default at 12 see request doc for details http://docs.python-requests.org/en/master/user/advanced/
        self.timeout = timeout

        LOG.debug("host is %s", host)
        resp_lic = self.monitor('license', 'status', vdom="global")
        LOG.debug("response monitor license: %s", resp_lic)
        self._fortiversion = resp_lic['version']
        return True


    def get_version(self):
        self.check_session()
        return self._fortiversion


    def get_mkeyname(self, path, name, vdom=None):
        # retreive the table mkey from schema
        schema = self.schema(path, name, vdom=vdom)
        try:
            keyname = schema['mkey']
        except KeyError:
            LOG.warning("there is no mkey for %s/%s", path, name)
            return False
        return keyname


    def get_mkey(self, path, name, data, vdom=None):
        # retreive the table mkey from schema

        keyname = self.get_mkeyname(path, name, vdom)
        if not keyname:
            LOG.warning("there is no mkey for %s/%s", path, name)
            return None
        else:
            try:
                mkey = data[keyname]
            except KeyError:
                LOG.warning("mkey %s not set in the data", mkey)
                return None
            return mkey


    def logout(self):
        url = self.url_prefix + '/logout'
        res = self._session.post(url, timeout=self.timeout)
        self._session.close()
        self._session.cookies.clear()
        self._logged = False
        # set license to Valid by default to ensure rechecked at login
        self._license = "Valid"
        self.logging(res)


    def cmdb_url(self, path, name, vdom=None, mkey=None):
        # all calls will start with a build url so checking login/license here is enough
        self.check_session()
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
        LOG.debug("urlbuild is %s with crsf: %s", url, self._session.headers)
        return url


    def mon_url(self, path, name, vdom=None, mkey=None):
        # all calls will start with a build url so checking login/license here is enough
        self.check_session()
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
        LOG.debug("in monitor url is %s", url)
        res = self._session.get(url, params=parameters, timeout=self.timeout)
        LOG.debug("in MONITOR function")
        return self.formatresponse(res, vdom=vdom)


    def download(self, path, name, vdom=None, mkey=None, parameters=None):
        url = self.mon_url(path, name, vdom=vdom, mkey=mkey)
        res = self._session.get(url, params=parameters, timeout=self.timeout)
        LOG.debug("in DOWNLOAD function")
        LOG.debug(" result download : %s", res.content)
        return res


    def upload(self, path, name, vdom=None, mkey=None,
               parameters=None, data=None, files=None):
        url = self.mon_url(path, name, vdom=vdom, mkey=mkey)
        res = self._session.post(url, params=parameters,
                                 data=data, files=files, timeout=self.timeout)
        LOG.debug("in UPLOAD function")
        return res


    def get(self, path, name, vdom=None, mkey=None, parameters=None):
        url = self.cmdb_url(path, name, vdom, mkey=mkey)
        LOG.debug("Calling GET ( %s, %s)", url, parameters)
        res = self._session.get(url, params=parameters, timeout=self.timeout)
        LOG.debug("in GET function")
        return self.formatresponse(res, vdom=vdom)


    def schema(self, path, name, vdom=None):
        # vdom or global is managed in cmdb_url
        if vdom is None:
            url = self.cmdb_url(path, name) + "?action=schema"
        else:
            url = self.cmdb_url(path, name, vdom=vdom) + "&action=schema"

        res = self._session.get(url, timeout=self.timeout)
        if res.status_code is 200:
            if vdom == "global":
                return json.loads(res.content.decode('utf-8'))[0]['results']
            else:
                return json.loads(res.content.decode('utf-8'))['results']
        else:
            return json.loads(res.content.decode('utf-8'))


    def get_name_path_dict(self, vdom=None):
        # return builded URL
        url_postfix = '/api/v2/cmdb/'
        if vdom is not None:
            url_postfix += '?vdom=' + vdom + "&action=schema"
        else:
            url_postfix += "?action=schema"

        url = self.url_prefix + url_postfix
        cmdbschema = self._session.get(url, timeout=self.timeout)
        self.logging(cmdbschema)
        j = json.loads(cmdbschema.content.decode('utf-8'))['results']
        dict = []
        for keys in j:
            if "__tree__" not in keys['path']:
                dict.append(keys['path'] + " " + keys['name'])
        return dict


    def post(self, path, name, data, vdom=None,
             mkey=None, parameters=None):
        # we always post to the upper name/path the mkey is in the data.
        # So we can ensure the data set is correctly filled in case mkey is passed.
        LOG.debug("in POST function")
        if mkey:
            mkeyname = self.get_mkeyname(path, name, vdom)
            LOG.debug("in post calculated mkeyname : %s mkey: %s ", mkeyname, mkey)
            # if mkey is forced on the function call then we change it in the data
            # even if inconsistent data/mkey is passed
            data[mkeyname] = mkey
        # post with mkey will return a 404 as the next level is not there yet
        # we pushed mkey in data if needed.
        url = self.cmdb_url(path, name, vdom, mkey=None)
        LOG.debug("POST sent data : %s", json.dumps(data))
        res = self._session.post(
            url, params=parameters, data=json.dumps(data), timeout=self.timeout)
        LOG.debug("POST raw results: %s", res)
        return self.formatresponse(res, vdom=vdom)


    def put(self, path, name, vdom=None,
            mkey=None, parameters=None, data=None):
        if not mkey:
            mkey = self.get_mkey(path, name, data, vdom=vdom)
        url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.put(url, params=parameters,
                                data=json.dumps(data), timeout=self.timeout)
        LOG.debug("in PUT function")
        return self.formatresponse(res, vdom=vdom)


    def move(self, path, name, vdom=None, mkey=None,
             where=None, reference_key=None, parameters={}):
        url = self.cmdb_url(path, name, vdom, mkey)
        parameters['action'] = 'move'
        parameters[where] = str(reference_key)
        res = self._session.put(url, params=parameters, timeout=self.timeout)
        LOG.debug("in MOVE function")
        return self.formatresponse(res, vdom=vdom)


    def delete(self, path, name, vdom=None,
               mkey=None, parameters=None, data=None):
        # Need to find the type of the mkey to avoid error when integer assume
        # the other types will be ok.
        if not mkey:
            mkey = self.get_mkey(path, name, data, vdom=vdom)
        url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.delete(
            url, params=parameters, data=json.dumps(data), timeout=self.timeout)

        LOG.debug("in DELETE function")
        return self.formatresponse(res, vdom=vdom)

    # Set will try to put if err code is 424 will try put (ressource exists)
    # may add a force option to delete and redo if troubles.
    def set(self, path, name, data, mkey=None, vdom=None, parameters=None):
        # post with mkey will return a 404 as the next level is not there yet
        if not mkey:
            mkey = self.get_mkey(path, name, data, vdom=vdom)
        url = self.cmdb_url(path, name, vdom, mkey)
        res = self._session.put(
            url, params=parameters, data=json.dumps(data), timeout=self.timeout)
        LOG.debug("in SET function after PUT")
        r = self.formatresponse(res, vdom=vdom)

        if r['http_status'] == 404 or r['http_status'] == 405 or r['http_status'] == 500:
            LOG.warning(
                "Try to put on %s  failed doing a put to force parameters\
                change consider delete if still fails ",
                res.request.url)
            res = self.post(path, name, data, vdom, mkey)
            LOG.debug("in SET function after POST result %s", res)
            return self.formatresponse(res, vdom=vdom)
        else:
            return r


    @staticmethod
    def ssh(cmds, host, user, password=None, port=22):
        """ Send a multi line string via ssh to the fortigate """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=port, username=user, password=password,
                       allow_agent=False, timeout=10)
        LOG.debug("ssh login to  %s:%s ", host, port)
        # commands is a multiline string using the ''' string ''' format
        try:
            stdin, stdout, stderr = client.exec_command(cmds)
        except:
            LOG.debug("exec_command failed")
            raise subprocess.CalledProcessError(returncode=retcode, cmd=cmds,
                                                output=output)
        LOG.debug("ssh command in:  %s out: %s err: %s ",
                  stdin, stdout, stderr)
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
        return ''.join(str(results)), ''.join(str(stderr.read().strip()))


    def license(self):
        # license check and update
        # GET /api/v2/monitor/license/status
        # force (exec update-now) with FortiGuard if invalid
        # POST api/v2/monitor/system/fortiguard/update
        resp = self.monitor('license', 'status')
        if resp['status'] == 'success':
            return resp
        else:
            # if license not valid we try to update and check again
            url = self.mon_url('system', 'fortiguard', mkey='update')
            postres = self._session.post(url, timeout=self.timeout)
            LOG.debug("Return POST fortiguard %s:", postres)
            postresp = json.loads(postres.content.decode('utf-8'))
            if postresp['status'] == 'success':
                time.sleep(17)
                return self.monitor('license', 'status')


    def setoverlayconfig(self, yamltree, vdom=None):
        # take a yaml tree with name: path: mkey: structure and recursively set the values.
        # create a copy to only keep the leaf as node (table firewall rules etc
        # Split the tree in 2 yaml objects

        yamltreel3 = OrderedDict()
        yamltreel3 = copy.deepcopy(yamltree)
        LOG.debug("intial yamltreel3 is %s ", yamltreel3)
        for name in yamltree.copy():
            for path in yamltree[name]:
                for k in yamltree[name][path].copy():
                    node = yamltree[name][path][k]
                    if isinstance(node, dict):
                        # if the node is a structure remove from yamltree keep in yamltreel3
                        LOG.debug("Delete yamltree k: %s node: %s ", k, node)
                        del yamltree[name][path][k]
                        LOG.debug("during DEL yamltreel3 is %s ", yamltreel3)
                    else:
                        # Should then be a string only so remove from yamltreel3
                        del yamltreel3[name][path]
        # yamltree and yamltreel3 are now differents
        LOG.debug("after yamltree is %s ", yamltree)
        LOG.debug("after yamltreel3 is %s ", yamltreel3)
        restree = False
        # Set the standard value on top of nodes first (example if setting firewall mode
        # it must be done before pushing a rule l3)
        # Set the standard value on top of nodes first (example if setting firewall mode it must be done before pushing a rule l3)
        for name in yamltree:
            for path in yamltree[name]:
                LOG.debug("iterate set in yamltree @ name: %s path %s value %s", name, path, yamltree[name][path])
                if yamltree[name][path]:
                    res = self.set(name, path, data=yamltree[name][path], vdom=vdom)
                    if res['status'] == "success":
                        restree = True
                    else:
                        restree = False
                        break

        for name in yamltreel3:
            for path in yamltreel3[name]:
                for k in yamltreel3[name][path].copy():
                    node = yamltreel3[name][path][k]
                    LOG.debug("iterate set in yamltreel3 @ node: %s value %s ", k, yamltreel3[name][path][k])
                    res = self.set(name, path, mkey=k, data=node, vdom=vdom)
                    if res['status'] == "success":
                        restree = True
                    else:
                        restree = False
                        break

        #   Must defined a coherent returned value out
        return restree
