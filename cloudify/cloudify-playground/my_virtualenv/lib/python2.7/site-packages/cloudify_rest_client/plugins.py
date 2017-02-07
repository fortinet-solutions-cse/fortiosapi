########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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
import urlparse
import contextlib

from cloudify_rest_client import bytes_stream_utils
from cloudify_rest_client.responses import ListResponse


class Plugin(dict):
    """
    Cloudify plugin.
    """
    def __init__(self, plugin):
        self.update(plugin)

    @property
    def id(self):
        """
        :return: The identifier of the plugin.
        """
        return self.get('id')

    @property
    def package_name(self):
        """
        :return: The plugin package name.
        """
        return self.get('package_name')

    @property
    def archive_name(self):
        """
        :return: The plugin archive name.
        """
        return self.get('archive_name')

    @property
    def package_source(self):
        """
        :return: The plugin source.
        """
        return self.get('package_source')

    @property
    def package_version(self):
        """
        :return: The package version.
        """
        return self.get('package_version')

    @property
    def supported_platform(self):
        """
        :return: The plugins supported platform.
        """
        return self.get('supported_platform')

    @property
    def distribution(self):
        """
        :return: The plugin compiled distribution.
        """
        return self.get('distribution')

    @property
    def distribution_version(self):
        """
        :return: The plugin compiled distribution version.
        """
        return self.get('distribution_version')

    @property
    def distribution_release(self):
        """
        :return: The plugin compiled distribution release.
        """
        return self.get('distribution_release')

    @property
    def wheels(self):
        """
        :return: The plugins included wheels.
        """
        return self.get('wheels')

    @property
    def excluded_wheels(self):
        """
        :return: The plugins excluded wheels.
        """
        return self.get('excluded_wheels')

    @property
    def supported_py_versions(self):
        """
        :return: The plugins supported python versions.
        """
        return self.get('supported_py_versions')

    @property
    def uploaded_at(self):
        """
        :return: The plugins upload time.
        """
        return self.get('uploaded_at')


class PluginsClient(object):
    """
    Cloudify's plugin management client.
    """
    def __init__(self, api):
        self.api = api

    def get(self, plugin_id, _include=None):
        """
        Gets a plugin by its id.

        :param plugin_id: Plugin's id to get.
        :param _include: List of fields to include in response.
        :return: The plugin details.
        """
        assert plugin_id
        uri = '/plugins/{0}'.format(plugin_id)
        response = self.api.get(uri, _include=_include)
        return Plugin(response)

    def list(self, _include=None, **kwargs):
        """
        Returns a list of available plugins.
        :param _include: List of fields to include in response.
        :return: Plugins list.
        """
        response = self.api.get('/plugins', _include=_include, params=kwargs)
        return ListResponse([Plugin(item) for item in response['items']],
                            response['metadata'])

    def delete(self, plugin_id, force=False):
        """
        Deletes the plugin whose id matches the provided plugin id.
        :param plugin_id: The id of the plugin to be deleted.
        :param force: Delete plugin even if there is a deployment
                      currently using it.
        :return: Deleted plugin by its ID.
        """
        assert plugin_id
        data = {
            'force': force
        }
        response = self.api.delete('/plugins/{0}'.format(plugin_id),
                                   data=data)
        return Plugin(response)

    def upload(self, plugin_path):
        """
        Uploads a plugin archive to the remote Cloudify manager plugins
        repository.
        :param plugin_path: Path to plugin archive.
        :return: Uploaded plugin.
        """
        assert plugin_path

        uri = '/plugins'
        query_params = {}

        if urlparse.urlparse(plugin_path).scheme and \
                not os.path.exists(plugin_path):
            query_params['plugin_archive_url'] = plugin_path
            data = None
        else:
            data = bytes_stream_utils.request_data_file_stream_gen(
                plugin_path)

        response = self.api.post(uri, params=query_params, data=data,
                                 expected_status_code=201)
        return Plugin(response)

    def download(self,
                 plugin_id,
                 output_file):
        """
        Downloads a previously uploaded plugin archive from the
        Cloudify manager.
        :param plugin_id: The plugin ID of the plugin to be downloaded.
        :param output_file: The file path of the downloaded plugin file
        :return: The file path of the downloaded plugin.
        """
        assert plugin_id
        uri = '/plugins/{0}/archive'.format(plugin_id)
        with contextlib.closing(self.api.get(uri, stream=True)) as response:
            output_file = bytes_stream_utils.write_response_stream_to_file(
                response, output_file)

            return output_file
