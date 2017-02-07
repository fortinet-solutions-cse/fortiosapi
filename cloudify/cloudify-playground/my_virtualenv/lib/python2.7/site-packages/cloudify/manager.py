########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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
import urllib2

import utils
from cloudify_rest_client import CloudifyClient
from cloudify.exceptions import HttpException, NonRecoverableError


class NodeInstance(object):
    """
    Represents a deployment node instance.
    An instance of this class contains runtime information retrieved
    from Cloudify's runtime storage as well as the node's state.
    """
    def __init__(self,
                 node_instance_id,
                 node_id,
                 runtime_properties=None,
                 state=None,
                 version=None,
                 host_id=None,
                 relationships=None):
        self.id = node_instance_id
        self._node_id = node_id
        self._runtime_properties = \
            DirtyTrackingDict((runtime_properties or {}).copy())
        self._state = state
        self._version = version
        self._host_id = host_id
        self._relationships = relationships

    def get(self, key):
        return self._runtime_properties.get(key)

    def put(self, key, value):
        self._runtime_properties[key] = value

    def delete(self, key):
        del(self._runtime_properties[key])

    __setitem__ = put

    __getitem__ = get

    __delitem__ = delete

    def __contains__(self, key):
        return key in self._runtime_properties

    @property
    def runtime_properties(self):
        """
        The node instance runtime properties.

        To update the properties, make changes on the returned dict and call
        ``update_node_instance`` with the modified instance.
        """
        return self._runtime_properties

    @property
    def version(self):
        return self._version

    @property
    def state(self):
        """
        The node instance state.

        To update the node instance state, change this property value and
        call ``update_node_instance`` with the modified instance.
        """
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def dirty(self):
        return self._runtime_properties.dirty

    @property
    def host_id(self):
        return self._host_id

    @property
    def node_id(self):
        return self._node_id

    @property
    def relationships(self):
        return self._relationships


def get_rest_client():
    """
    :returns: A REST client configured to connect to the manager in context
    :rtype: cloudify_rest_client.CloudifyClient
    """
    headers = None
    if utils.get_is_bypass_maintenance():
        headers = {'X-BYPASS-MAINTENANCE': 'True'}
    return CloudifyClient(utils.get_manager_ip(),
                          utils.get_manager_rest_service_port(),
                          headers=headers)


def _save_resource(logger, resource, resource_path, target_path):
    if not target_path:
        target_path = os.path.join(utils.create_temp_folder(),
                                   os.path.basename(resource_path))
    with open(target_path, 'wb') as f:
        f.write(resource)
    logger.info("Downloaded %s to %s" % (resource_path, target_path))
    return target_path


def download_resource_from_manager(resource_path, logger, target_path=None):
    """
    Download resource from the manager file server.

    :param resource_path: path to resource on the file server
    :param logger: logger to use for info output
    :param target_path: optional target path for the resource
    :returns: path to the downloaded resource
    """
    resource = get_resource_from_manager(resource_path)
    return _save_resource(logger, resource, resource_path, target_path)


def download_resource(blueprint_id,
                      deployment_id,
                      resource_path,
                      logger,
                      target_path=None):
    """
    Download resource from the manager file server with path relative to
    the deployment or blueprint denoted by ``deployment_id`` or
    ``blueprint_id``

    An attempt will first be made for getting the resource from the deployment
    folder. If not found, an attempt will be made for getting the resource
    from the blueprint folder.

    :param blueprint_id: the blueprint id of the blueprint to download the
                         resource from
    :param deployment_id: the deployment id of the deployment to download the
                          resource from
    :param resource_path: path to resource relative to blueprint or deployment
                          folder
    :param logger: logger to use for info output
    :param target_path: optional target path for the resource
    :returns: path to the downloaded resource
    """
    resource = get_resource(blueprint_id,
                            deployment_id,
                            resource_path)
    return _save_resource(logger, resource, resource_path, target_path)


def get_resource_from_manager(resource_path, base_url=None):
    """
    Get resource from the manager file server.

    :param resource_path: path to resource on the file server
    :returns: resource content
    """
    if base_url is None:
        base_url = utils.get_manager_file_server_url()
    try:
        url = '{0}/{1}'.format(base_url, resource_path)
        response = urllib2.urlopen(url)
        return response.read()
    except urllib2.HTTPError as e:
        raise HttpException(e.url, e.code, e.msg)


def get_resource(blueprint_id, deployment_id, resource_path):
    """
    Get resource from the manager file server with path relative to
    the deployment or blueprint denoted by ``deployment_id`` or
    ``blueprint_id``.

    An attempt will first be made for getting the resource from the deployment
    folder. If not found, an attempt will be made for getting the resource
    from the blueprint folder.

    :param blueprint_id: the blueprint id of the blueprint to download
                         the resource from
    :param deployment_id: the deployment id of the deployment to download the
                          resource from
    :param resource_path: path to resource relative to blueprint folder
    :returns: resource content
    """

    def _get_resource(base_url):
        try:
            return get_resource_from_manager(resource_path, base_url=base_url)
        except HttpException as e:
            if e.code != 404:
                raise
            return None

    resource = None
    if deployment_id is not None:
        deployment_base_url = '{0}/{1}'.format(
            utils.get_manager_file_server_deployments_root_url(),
            deployment_id)
        resource = _get_resource(deployment_base_url)

    if resource is None:
        blueprint_base_url = '{0}/{1}'.format(
                utils.get_manager_file_server_blueprints_root_url(),
                blueprint_id)
        resource = _get_resource(blueprint_base_url)
        if resource is None:
            if deployment_id is None:
                url = blueprint_base_url
            else:
                url = ','.join([deployment_base_url, blueprint_base_url])
            raise HttpException(url, 404, 'Resource not found: {0}'
                                .format(resource_path))
    return resource


def get_node_instance(node_instance_id):
    """
    Read node instance data from the storage.

    :param node_instance_id: the node instance id
    :rtype: NodeInstance
    """
    client = get_rest_client()
    instance = client.node_instances.get(node_instance_id)
    return NodeInstance(node_instance_id,
                        instance.node_id,
                        runtime_properties=instance.runtime_properties,
                        state=instance.state,
                        version=instance.version,
                        host_id=instance.host_id,
                        relationships=instance.relationships)


def update_node_instance(node_instance):
    """
    Update node instance data changes in the storage.

    :param node_instance: the node instance with the updated data
    """
    client = get_rest_client()
    client.node_instances.update(
        node_instance.id,
        state=node_instance.state,
        runtime_properties=node_instance.runtime_properties,
        version=node_instance.version)


def get_node_instance_ip(node_instance_id):
    """
    Get the IP address of the host the node instance denoted by
    ``node_instance_id`` is contained in.
    """
    client = get_rest_client()
    instance = client.node_instances.get(node_instance_id)
    if instance.host_id is None:
        raise NonRecoverableError('node instance: {0} is missing host_id'
                                  'property'.format(instance.id))
    if node_instance_id != instance.host_id:
        instance = client.node_instances.get(instance.host_id)
    if instance.runtime_properties.get('ip'):
        return instance.runtime_properties['ip']
    node = client.nodes.get(instance.deployment_id, instance.node_id)
    if node.properties.get('ip'):
        return node.properties['ip']
    raise NonRecoverableError('could not find ip for node instance: {0} with '
                              'host id: {1}'.format(node_instance_id,
                                                    instance.id))


# TODO: some nasty code duplication between these two methods


def update_execution_status(execution_id, status, error=None):
    """
    Update the execution status of the execution denoted by ``execution_id``.

    :returns: The updated status
    """
    client = get_rest_client()
    return client.executions.update(execution_id, status, error)


def get_bootstrap_context():
    """Read the manager bootstrap context."""
    client = get_rest_client()
    context = client.manager.get_context()['context']
    return context.get('cloudify', {})


def get_provider_context():
    """Read the manager provider context."""
    client = get_rest_client()
    context = client.manager.get_context()
    return context['context']


class DirtyTrackingDict(dict):

    def __init__(self, *args, **kwargs):
        super(DirtyTrackingDict, self).__init__(*args, **kwargs)
        self.modifiable = True
        self.dirty = False

    def __setitem__(self, key, value):
        r = super(DirtyTrackingDict, self).__setitem__(key, value)
        self._set_changed()
        return r

    def __delitem__(self, key):
        r = super(DirtyTrackingDict, self).__delitem__(key)
        self._set_changed()
        return r

    def update(self, E=None, **F):
        r = super(DirtyTrackingDict, self).update(E, **F)
        self._set_changed()
        return r

    def clear(self):
        r = super(DirtyTrackingDict, self).clear()
        self._set_changed()
        return r

    def pop(self, k, d=None):
        r = super(DirtyTrackingDict, self).pop(k, d)
        self._set_changed()
        return r

    def popitem(self):
        r = super(DirtyTrackingDict, self).popitem()
        self._set_changed()
        return r

    def _set_changed(self):
        # python 2.6 doesn't have modifiable during copy.deepcopy
        if hasattr(self, 'modifiable') and not self.modifiable:
            raise NonRecoverableError('Cannot modify runtime properties of'
                                      ' relationship node instances')
        self.dirty = True
