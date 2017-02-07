########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
import os
import json
import urllib
import shutil
import urlparse
import tempfile
from mimetypes import MimeTypes

from requests_toolbelt.multipart.encoder import MultipartEncoder

from cloudify_rest_client import utils
from cloudify_rest_client.responses import ListResponse


class DeploymentUpdate(dict):

    def __init__(self, update):
        self.update(update)

    @property
    def id(self):
        """Deployment update id"""
        return self['id']

    @property
    def state(self):
        """Deployment update status"""
        return self['state']

    @property
    def deployment_id(self):
        """Deployment Id the outputs belong to."""
        return self['deployment_id']

    @property
    def steps(self):
        return self['steps']

    @property
    def execution_id(self):
        return self['execution_id']

    @property
    def created_at(self):
        return self['created_at']


class DeploymentUpdatesClient(object):

    def __init__(self, api):
        self.api = api

    def list(self, _include=None, **kwargs):
        """List deployment updates

        :param deployment_id: The deployment id (optional)
        :param kwargs: Optional filter fields. for a list of available fields
               see the REST service's models.DeploymentUpdate.fields
        """

        uri = '/deployment-updates'

        response = self.api.get(uri, params=kwargs, _include=_include)
        items = [DeploymentUpdate(item) for item in response['items']]
        return ListResponse(items, response['metadata'])

    def _update_from_blueprint(self,
                               deployment_id,
                               blueprint_path,
                               inputs=None):
        """Create a deployment update transaction for blueprint app.

        :param deployment_id: The deployment id
        :param blueprint_path: the path of the blueprint to stage
        """
        assert deployment_id

        tempdir = tempfile.mkdtemp()
        try:
            tar_path = utils.tar_blueprint(blueprint_path, tempdir)
            application_filename = os.path.basename(blueprint_path)

            return self._update_from_archive(deployment_id,
                                             tar_path,
                                             application_filename,
                                             inputs=inputs)
        finally:
            shutil.rmtree(tempdir)

    @staticmethod
    def _update_from_archive(deployment_id,
                             archive_path,
                             application_file_name=None,
                             inputs=None):
        """Create a deployment update transaction for an archived app.

        :param archive_path: the path for the archived app.
        :param application_file_name: the main blueprint filename.
        :param deployment_id: the deployment id to update.
        :return: DeploymentUpdate dict
        :rtype: DeploymentUpdate
        """
        assert deployment_id

        mime_types = MimeTypes()

        data_form = {}
        params = {}
        # all the inputs are passed through the query
        if inputs:
            inputs_file = tempfile.TemporaryFile()
            json.dump(inputs, inputs_file)
            inputs_file.seek(0)
            data_form['inputs'] = ('inputs', inputs_file, 'text/plain')

        if application_file_name:
            params['application_file_name'] = \
                urllib.quote(application_file_name)

        # For a Windows path (e.g. "C:\aaa\bbb.zip") scheme is the
        # drive letter and therefore the 2nd condition is present
        if all([urlparse.urlparse(archive_path).scheme,
                not os.path.exists(archive_path)]):
            # archive location is URL
            params['blueprint_archive_url'] = archive_path
        else:
            data_form['blueprint_archive'] = (
                os.path.basename(archive_path),
                open(archive_path, 'rb'),
                # Guess the archive mime type
                mime_types.guess_type(urllib.pathname2url(archive_path)))

        return data_form, params

    def get(self, update_id, _include=None):
        """Get deployment update

        :param update_id: The update id
        """
        uri = '/deployment-updates/{0}'.format(update_id)
        response = self.api.get(uri, _include=_include)
        return DeploymentUpdate(response)

    def update(self,
               deployment_id,
               blueprint_or_archive_path,
               application_file_name=None,
               inputs=None,
               skip_install=False,
               skip_uninstall=False,
               workflow_id=None,
               force=False):

        # TODO better handle testing for a supported archive. in other commands
        # it is done in the cli part (`commands.<command_name>)
        if utils.is_supported_archive_type(blueprint_or_archive_path):
            data_form, params = \
                self._update_from_archive(deployment_id,
                                          blueprint_or_archive_path,
                                          application_file_name,
                                          inputs=inputs)
        else:
            data_form, params = \
                self._update_from_blueprint(deployment_id,
                                            blueprint_or_archive_path,
                                            inputs=inputs)

        if workflow_id:
            params['workflow_id'] = workflow_id
        if skip_install:
            params['skip_install'] = skip_install
        if skip_uninstall:
            params['skip_uninstall'] = skip_uninstall
        if force:
            params['force'] = force

        data_and_headers = {}

        if data_form:
            data = MultipartEncoder(fields=data_form)
            data_and_headers['data'] = data
            data_and_headers['headers'] = {'Content-type': data.content_type}

        uri = '/deployment-updates/{0}/update/initiate'.format(deployment_id)
        response = self.api.post(uri, params=params, **data_and_headers)

        return DeploymentUpdate(response)

    def finalize_commit(self, update_id):
        """Finalize the commiting process

        :param update_id:
        :return:
        """
        assert update_id

        uri = '/deployment-updates/{0}/update/finalize'.format(update_id)
        response = self.api.post(uri)
        return DeploymentUpdate(response)
