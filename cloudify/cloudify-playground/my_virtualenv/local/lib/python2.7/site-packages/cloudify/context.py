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

import errno
import os
import warnings

from cloudify.endpoint import ManagerEndpoint, LocalEndpoint
from cloudify.logs import init_cloudify_logger
from cloudify import constants
from cloudify import exceptions
from cloudify import utils


DEPLOYMENT = 'deployment'
NODE_INSTANCE = 'node-instance'
RELATIONSHIP_INSTANCE = 'relationship-instance'


class ContextCapabilities(object):
    """Maps from instance relationship target ids to their respective
    runtime properties
    """
    def __init__(self, endpoint, instance):
        self._endpoint = endpoint
        self.instance = instance
        self._relationship_runtimes = None

    def _find_item(self, key):
        """
        Returns the capability for the provided key by iterating through all
        dependency nodes available capabilities.
        """
        ls = [caps for caps in self._capabilities.values() if key in caps]
        if len(ls) == 0:
            return False, None
        if len(ls) > 1:
            raise exceptions.NonRecoverableError(
                "'{0}' capability ambiguity [capabilities={1}]".format(
                    key, self._capabilities))
        return True, ls[0][key]

    def __getitem__(self, key):
        found, value = self._find_item(key)
        if not found:
            raise exceptions.NonRecoverableError(
                "capability '{0}' not found [capabilities={1}]".format(
                    key, self._capabilities))
        return value

    def __contains__(self, key):
        found, _ = self._find_item(key)
        return found

    def get_all(self):
        """Returns all capabilities as dict."""
        return self._capabilities

    def __str__(self):
        return ('<' + self.__class__.__name__ + ' ' +
                str(self._capabilities) + '>')

    @property
    def _capabilities(self):
        if self._relationship_runtimes is None:
            self._relationship_runtimes = {}
            for relationship in self.instance.relationships:
                self._relationship_runtimes.update({
                    relationship.target.instance.id:
                    relationship.target.instance.runtime_properties
                })
        return self._relationship_runtimes


class CommonContext(object):

    def __init__(self, ctx=None):
        self._context = ctx or {}
        self._local = ctx.get('local', False)
        if self._local:
            # there are times when this instance is instantiated merely for
            # accessing the attributes so we can tolerate no storage (such is
            # the case in logging)
            self._endpoint = LocalEndpoint(self, ctx.get('storage'))
        else:
            self._endpoint = ManagerEndpoint(self)

        self.blueprint = BlueprintContext(self._context)
        self.deployment = DeploymentContext(self._context)


class BootstrapContext(object):
    """
    Holds bootstrap context that was posted to the rest service. (usually
    during the bootstrap process).
    """

    class PolicyEngine(object):
        """Cloudify policy engine related configuration"""

        def __init__(self, policy_engine):
            self._policy_engine = policy_engine

        @property
        def start_timeout(self):
            """
            Returns the number of seconds to wait for the policy engine
            to start
            """
            return self._policy_engine.get('start_timeout')

    class CloudifyAgent(object):
        """Cloudify agent related bootstrap context properties."""

        def __init__(self, cloudify_agent):
            self._cloudify_agent = cloudify_agent

        @property
        def min_workers(self):
            """Returns the minimum number of workers for agent hosts."""
            return self._cloudify_agent.get('min_workers')

        @property
        def max_workers(self):
            """Returns the maximum number of workers for agent hosts."""
            return self._cloudify_agent.get('max_workers')

        @property
        def user(self):
            """
            Returns the username used when SSH-ing during agent
            installation.
            """
            return self._cloudify_agent.get('user')

        @property
        def remote_execution_port(self):
            """
            Returns the port used when SSH-ing during agent
            installation.
            """
            return self._cloudify_agent.get('remote_execution_port')

        @property
        def agent_key_path(self):
            """
            Returns the path to the key file on the management machine
            used when SSH-ing during agent installation.
            """
            return self._cloudify_agent.get('agent_key_path')

        @property
        def broker_ip(self):
            """
            Returns the IP for connecting to rabbit.
            An empty string should result in clients using the manager IP.
            """
            return self._cloudify_agent.get('broker_ip')

        @property
        def broker_user(self):
            """
            Returns the username for connecting to rabbit.
            """
            return self._cloudify_agent.get('broker_user')

        @property
        def broker_pass(self):
            """
            Returns the password for connecting to rabbit.
            """
            return self._cloudify_agent.get('broker_pass')

        @property
        def broker_ssl_enabled(self):
            """
            Returns whether SSL is enabled for connecting to rabbit.
            """
            return self._cloudify_agent.get('broker_ssl_enabled')

        @property
        def broker_ssl_cert(self):
            """
            Returns the SSL public cert for connecting to rabbit.
            """
            return self._cloudify_agent.get('broker_ssl_cert')

    def __init__(self, bootstrap_context):
        self._bootstrap_context = bootstrap_context

        cloudify_agent = bootstrap_context.get('cloudify_agent', {})
        policy_engine = bootstrap_context.get('policy_engine', {})
        self._cloudify_agent = self.CloudifyAgent(cloudify_agent)
        self._policy_engine = self.PolicyEngine(policy_engine)

    @property
    def cloudify_agent(self):
        """
        Returns Cloudify agent related bootstrap context data

        :rtype: CloudifyAgent
        """
        return self._cloudify_agent

    @property
    def policy_engine(self):
        """
        Returns Cloudify policy engine related bootstrap context data

        :rtype: PolicyEngine
        """
        return self._policy_engine

    @property
    def resources_prefix(self):
        """
        Returns the resources prefix that was configured during bootstrap.
        An empty string is returned if the resources prefix was not configured.
        """
        return self._bootstrap_context.get('resources_prefix', '')

    def broker_config(self, fallback_to_manager_ip=True):
        """
        Returns dictionary containing broker configuration.

        :param fallback_to_manager_ip: If True and there is no broker_ip in
        context, manager ip will be used. Note that manager ip detection is
        only possible within agent.
        """
        attributes = {}
        bootstrap_agent = self.cloudify_agent
        broker_user, broker_pass = utils.internal.get_broker_credentials(
            bootstrap_agent
        )
        if bootstrap_agent.broker_ip:
            attributes['broker_ip'] = bootstrap_agent.broker_ip
        elif fallback_to_manager_ip:
            attributes['broker_ip'] = utils.get_manager_ip()
        attributes['broker_user'] = broker_user
        attributes['broker_pass'] = broker_pass
        attributes['broker_ssl_enabled'] = bootstrap_agent.broker_ssl_enabled
        attributes['broker_ssl_cert'] = bootstrap_agent.broker_ssl_cert
        if bootstrap_agent.broker_ssl_enabled:
            broker_port = constants.BROKER_PORT_SSL
        else:
            broker_port = constants.BROKER_PORT_NO_SSL
        attributes['broker_port'] = broker_port
        return attributes


class EntityContext(object):

    def __init__(self, context, **_):
        self._context = context


class BlueprintContext(EntityContext):

    @property
    def id(self):
        """The blueprint id the plugin invocation belongs to."""
        return self._context.get('blueprint_id')


class DeploymentContext(EntityContext):

    @property
    def id(self):
        """The deployment id the plugin invocation belongs to."""
        return self._context.get('deployment_id')


class NodeContext(EntityContext):

    def __init__(self, *args, **kwargs):
        super(NodeContext, self).__init__(*args, **kwargs)
        self._endpoint = kwargs['endpoint']
        self._node = None

    def _get_node_if_needed(self):
        if self._node is None:
            self._node = self._endpoint.get_node(self.id)
            props = self._node.get('properties', {})
            self._node['properties'] = ImmutableProperties(props)

    @property
    def id(self):
        """The node's id"""
        return self.name

    @property
    def name(self):
        """The node's name"""
        return self._context.get('node_name')

    @property
    def properties(self):
        """The node properties as dict (read-only).
        These properties are the properties specified in the blueprint.
        """
        self._get_node_if_needed()
        return self._node.properties

    @property
    def type(self):
        """The node's type"""
        self._get_node_if_needed()
        return self._node.type

    @property
    def type_hierarchy(self):
        """The node's type hierarchy"""
        self._get_node_if_needed()
        return self._node.type_hierarchy


class NodeInstanceContext(EntityContext):

    def __init__(self, *args, **kwargs):
        super(NodeInstanceContext, self).__init__(*args, **kwargs)
        self._endpoint = kwargs['endpoint']
        self._node = kwargs['node']
        self._modifiable = kwargs['modifiable']
        self._node_instance = None
        self._host_ip = None
        self._relationships = None

    def _get_node_instance_if_needed(self):
        if self._node_instance is None:
            self._node_instance = self._endpoint.get_node_instance(self.id)
            self._node_instance.runtime_properties.modifiable = \
                self._modifiable

    @property
    def id(self):
        """The node instance id."""
        return self._context.get('node_id')

    @property
    def runtime_properties(self):
        """The node instance runtime properties as a dict (read-only).

        Runtime properties are properties set during the node instance's
        lifecycle.
        Retrieving runtime properties involves a call to Cloudify's storage.
        """
        self._get_node_instance_if_needed()
        return self._node_instance.runtime_properties

    def update(self):
        """
        Stores new/updated runtime properties for the node instance in context
        in Cloudify's storage.

        This method should be invoked only if its necessary to immediately
        update Cloudify's storage with changes. Otherwise, the method is
        automatically invoked as soon as the task execution is over.
        """
        if self._node_instance is not None and self._node_instance.dirty:
            self._endpoint.update_node_instance(self._node_instance)
            self._node_instance = None

    def _get_node_instance_ip_if_needed(self):
        self._get_node_instance_if_needed()
        if self._host_ip is None:
            if self.id == self._node_instance.host_id:
                self._host_ip = self._endpoint.get_host_node_instance_ip(
                    host_id=self.id,
                    properties=self._node.properties,
                    runtime_properties=self.runtime_properties)
            else:
                self._host_ip = self._endpoint.get_host_node_instance_ip(
                    host_id=self._node_instance.host_id)

    @property
    def host_ip(self):
        """
        Returns the node instance host ip address.

        This values is derived by reading the ``host_id`` from the relevant
        node instance and then reading its ``ip`` runtime property or its
        node_state ``ip`` property.
        """

        self._get_node_instance_ip_if_needed()
        return self._host_ip

    @property
    def relationships(self):
        """Returns a list of this instance relationships

        :return: list of RelationshipContext
        :rtype: list
        """
        self._get_node_instance_if_needed()
        if self._relationships is None:
            self._relationships = [
                RelationshipContext(relationship, self._endpoint, self._node)
                for relationship in self._node_instance.relationships]
        return self._relationships


class RelationshipContext(EntityContext):
    """Holds relationship instance data"""

    def __init__(self, relationship_context, endpoint, node):
        super(RelationshipContext, self).__init__(relationship_context)
        self._node = node
        target_context = {
            'node_name': relationship_context['target_name'],
            'node_id': relationship_context['target_id']
        }
        self._target = RelationshipSubjectContext(target_context, endpoint,
                                                  modifiable=False)
        self._type_hierarchy = None

    @property
    def target(self):
        """Returns a holder for target node and target instance

        :rtype: RelationshipSubjectContext
        """
        return self._target

    @property
    def type(self):
        """The relationship type"""
        return self._context.get('type')

    @property
    def type_hierarchy(self):
        """The relationship type hierarchy"""
        if self._type_hierarchy is None:
            self._node._get_node_if_needed()
            node_relationships = self._node._node.relationships
            self._type_hierarchy = [
                r for r in node_relationships if
                r['type'] == self.type][0]['type_hierarchy']
        return self._type_hierarchy


class RelationshipSubjectContext(object):
    """Holds reference to node and node instance.

    Obtained in relationship operations by `ctx.source` and `ctx.target`, and
    by iterating instance relationships and for each relationship, reading
    `relationship.target`
    """

    def __init__(self, context, endpoint, modifiable):
        self._context = context
        self.node = NodeContext(context,
                                endpoint=endpoint)
        self.instance = NodeInstanceContext(context,
                                            endpoint=endpoint,
                                            node=self.node,
                                            modifiable=modifiable)


class CloudifyContext(CommonContext):
    """
    A context object passed to plugins tasks invocations.
    The context object is used in plugins when interacting with
    the Cloudify environment::

        from cloudify import ctx

        @operation
        def my_start(**kwargs):
            # port is a property that was configured on the current instance's
            # node
            port = ctx.node.properties['port']
            start_server(port=port)

    """
    def __init__(self, ctx=None):
        super(CloudifyContext, self).__init__(ctx=ctx)

        self._logger = None
        self._provider_context = None
        self._bootstrap_context = None
        self._host_ip = None
        self._node = None
        self._instance = None
        self._source = None
        self._target = None
        self._operation = OperationContext(self._context.get('operation', {}))
        self._agent = CloudifyAgentContext(self)

        capabilities_node_instance = None
        if 'related' in self._context:
            if self._context['related']['is_target']:
                source_context = self._context
                target_context = self._context['related']
            else:
                source_context = self._context['related']
                target_context = self._context
            self._source = RelationshipSubjectContext(source_context,
                                                      self._endpoint,
                                                      modifiable=True)
            self._target = RelationshipSubjectContext(target_context,
                                                      self._endpoint,
                                                      modifiable=True)
            if self._context['related']['is_target']:
                capabilities_node_instance = self._source.instance
            else:
                capabilities_node_instance = self._target.instance

        elif self._context.get('node_id'):
            self._node = NodeContext(self._context,
                                     endpoint=self._endpoint)
            self._instance = NodeInstanceContext(self._context,
                                                 endpoint=self._endpoint,
                                                 node=self._node,
                                                 modifiable=True)
            capabilities_node_instance = self._instance

        self._capabilities = ContextCapabilities(self._endpoint,
                                                 capabilities_node_instance)

        plugin = self._context.get('plugin', {})
        # Because we inherit from str, we can't really change the constructor
        # only augment it.
        self._plugin = PluginContext(plugin.get('name', ''))
        self._plugin._plugin_context = plugin
        self._plugin._deployment_id = self.deployment.id
        self._plugin._endpoint = self._endpoint

    def _verify_in_node_context(self):
        if self.type != NODE_INSTANCE:
            raise exceptions.NonRecoverableError(
                'ctx.node/ctx.instance can only be used in a {0} context but '
                'used in a {1} context.'.format(NODE_INSTANCE, self.type))

    def _verify_in_relationship_context(self):
        if self.type != RELATIONSHIP_INSTANCE:
            raise exceptions.NonRecoverableError(
                'ctx.source/ctx.target can only be used in a {0} context but '
                'used in a {1} context.'.format(RELATIONSHIP_INSTANCE,
                                                self.type))

    def _verify_in_node_or_relationship_context(self):
        if self.type not in [NODE_INSTANCE, RELATIONSHIP_INSTANCE]:
            raise exceptions.NonRecoverableError(
                'capabilities can only be used in a {0}/{1} context but '
                'used in a {2} context.'.format(NODE_INSTANCE,
                                                RELATIONSHIP_INSTANCE,
                                                self.type))

    @property
    def instance(self):
        """The node instance the operation is executed for.

        This property is only relevant for NODE_INSTANCE context operations.
        """
        self._verify_in_node_context()
        return self._instance

    @property
    def node(self):
        """The node the operation is executed for.

        This property is only relevant for NODE_INSTANCE context operations.
        """
        self._verify_in_node_context()
        return self._node

    @property
    def source(self):
        """Provides access to the relationship's operation source node and
        node instance.

        This property is only relevant for relationship operations.
        """
        self._verify_in_relationship_context()
        return self._source

    @property
    def target(self):
        """Provides access to the relationship's operation target node and
        node instance.

        This property is only relevant for relationship operations.
        """
        self._verify_in_relationship_context()
        return self._target

    @property
    def type(self):
        """The type of this context.

        Available values:

        - DEPLOYMENT
        - NODE_INSTANCE
        - RELATIONSHIP_INSTANCE
        """
        if self._source:
            return RELATIONSHIP_INSTANCE
        if self._instance:
            return NODE_INSTANCE
        return DEPLOYMENT

    @property
    def execution_id(self):
        """
        The workflow execution id the plugin invocation was requested from.
        This is a unique value which identifies a specific workflow execution.
        """
        return self._context.get('execution_id')

    @property
    def workflow_id(self):
        """
        The workflow id the plugin invocation was requested from.
        For example:

         ``install``, ``uninstall`` etc...
        """
        return self._context.get('workflow_id')

    @property
    def task_id(self):
        """The plugin's task invocation unique id."""
        return self._context.get('task_id')

    @property
    def task_name(self):
        """The full task name of the invoked task."""
        return self._context.get('task_name')

    @property
    def task_target(self):
        """The task target (celery worker name)."""
        return self._context.get('task_target')

    @property
    def task_queue(self):
        """The task target (celery queue name)."""
        return self._context.get('task_queue')

    @property
    def plugin(self):
        """The plugin context."""
        return self._plugin

    @property
    def operation(self):
        """
        The current operation context.
        """
        return self._operation

    @property
    def agent(self):
        self._verify_in_node_context()
        if constants.COMPUTE_NODE_TYPE not in self.node.type_hierarchy:
            raise exceptions.NonRecoverableError(
                'ctx.agent can only be used with compute nodes but current '
                'node is of type: {0}'.format(self.node.type))
        return self._agent

    @property
    def capabilities(self):
        """Maps from instance relationship target ids to their respective
        runtime properties

        NOTE: This feature is deprecated, use 'instance.relationships' instead.
        """
        self._verify_in_node_or_relationship_context()
        warnings.warn('capabilities is deprecated, use instance.relationships'
                      'instead', DeprecationWarning)
        return self._capabilities

    @property
    def logger(self):
        """
        A Cloudify context aware logger.

        Use this logger in order to index logged messages in ElasticSearch
        using logstash.
        """
        if self._logger is None:
            self._logger = self._init_cloudify_logger()
        return self._logger

    @property
    def bootstrap_context(self):
        """
        System context provided during the bootstrap process

        :rtype: BootstrapContext
        """
        if self._bootstrap_context is None:
            context = self._endpoint.get_bootstrap_context()
            self._bootstrap_context = BootstrapContext(context)
        return self._bootstrap_context

    def send_event(self, event):
        """
        Send an event to rabbitmq

        :param event: the event message
        """
        self._endpoint.send_plugin_event(message=event)

    @property
    def provider_context(self):
        """Gets provider context which contains provider specific metadata."""
        if self._provider_context is None:
            self._provider_context = self._endpoint.get_provider_context()
        return self._provider_context

    def get_resource(self,
                     resource_path):
        """
        Retrieves a resource bundled with the blueprint as a string.

        :param resource_path: the path to the resource. Note that this path is
                              relative to the blueprint file which was
                              uploaded.
        """

        return self._endpoint.get_resource(
            blueprint_id=self.blueprint.id,
            deployment_id=self.deployment.id,
            resource_path=resource_path)

    def get_resource_and_render(self,
                                resource_path,
                                template_variables=None):
        """
        Like get_resource, but also renders the resource according
        to template_variables.
        This context is added to template_variables.

        :param template_variables: according to this dict the
                                   resource will be rendered.
        """

        template_variables = self._add_context_to_template_variables(
            template_variables)
        return self._endpoint.get_resource(
            blueprint_id=self.blueprint.id,
            deployment_id=self.deployment.id,
            resource_path=resource_path,
            template_variables=template_variables)

    def download_resource(self,
                          resource_path,
                          target_path=None):
        """
        Retrieves a resource bundled with the blueprint and saves it under a
        local file.

        :param resource_path: the path to the resource. Note that this path is
                              relative to the blueprint file which was
                              uploaded.

        :param target_path: optional local path (including filename) to store
                            the resource at on the local file system.
                            If missing, the location will be a tempfile with a
                            generated name.

        :returns: The path to the resource on the local file system (identical
                  to target_path parameter if used).

                  raises an ``cloudify.exceptions.HttpException``

        :raises: ``cloudify.exceptions.HttpException`` on any kind
                 of HTTP Error.

        :raises: ``IOError`` if the resource
                 failed to be written to the local file system.

        """

        return self._endpoint.download_resource(
            blueprint_id=self.blueprint.id,
            deployment_id=self.deployment.id,
            resource_path=resource_path,
            logger=self.logger,
            target_path=target_path)

    def download_resource_and_render(self,
                                     resource_path,
                                     target_path=None,
                                     template_variables=None):
        """
        Like download_resource, but also renders the resource according
        to template_variables.
        This context is added to template_variables.

        :param template_variables: according to this dict the resource
                                   will be rendered.

        """

        template_variables = self._add_context_to_template_variables(
            template_variables)
        return self._endpoint.download_resource(
            blueprint_id=self.blueprint.id,
            deployment_id=self.deployment.id,
            resource_path=resource_path,
            logger=self.logger,
            target_path=target_path,
            template_variables=template_variables)

    def _init_cloudify_logger(self):
        logger_name = self.task_id if self.task_id is not None \
            else 'cloudify_plugin'
        handler = self._endpoint.get_logging_handler()
        return init_cloudify_logger(handler, logger_name)

    def _add_context_to_template_variables(self, template_variables):

        if template_variables:
            if 'ctx' in template_variables:
                raise exceptions.NonRecoverableError(
                    'Key not allowed - a key named '
                    'ctx is in template_variables')
        else:
            template_variables = {}

        template_variables['ctx'] = self
        return template_variables


class OperationContext(object):

    def __init__(self, operation_context):
        self._operation_context = operation_context or {}
        if not isinstance(self._operation_context, dict):
            raise exceptions.NonRecoverableError(
                'operation_context is expected to be a dict but is:'
                '{0}'.format(self._operation_context))
        self._operation_retry = None

    @property
    def name(self):
        """The name of the operation."""
        return self._operation_context.get('name')

    @property
    def retry_number(self):
        """The retry number (relevant for retries and recoverable errors)."""
        return self._operation_context.get('retry_number')

    @property
    def max_retries(self):
        """The maximum number of retries the operation can have."""
        return self._operation_context.get('max_retries')

    def retry(self, message=None, retry_after=None):
        """Specifies that this operation should be retried.

        Usage:
          return ctx.operation.retry(message='...', retry_after=1000)

        :param message A text message containing information about the reason
                       for retrying the operation.
        :param retry_after How many seconds should the workflow engine wait
                           before re-executing the operation.
        """
        self._operation_retry = exceptions.OperationRetry(
            message=message,
            retry_after=retry_after)


class CloudifyAgentContext(object):

    def __init__(self, context):
        self.context = context

    def init_script(self, agent_config=None):
        if (utils.internal.get_install_method(
                self.context.node.properties) not in
                constants.AGENT_INSTALL_METHODS_SCRIPTS):
            return None
        try:
            from cloudify_agent.installer import script
        except ImportError as e:
            raise exceptions.NonRecoverableError(
                'init_script cannot be used outside of an agent environment: '
                'ImportError: {0}'.format(e))
        return script.init_script(cloudify_agent=agent_config)


# inherits from `str` to maintain backwards compatibility
# with plugins that assume ctx.plugin will return the plugin name
# ctx.plugin == name should be deprecated and this workaround should
# be removed at some point
class PluginContext(str):

    def __init__(self, other=''):
        # These are set explicitly after PluginContext is instantiated
        self._plugin_context = {}
        self._deployment_id = None
        self._endpoint = None

    @property
    def name(self):
        """The plugin name."""
        return self._plugin_context.get('name', '')

    @property
    def package_name(self):
        """The plugin package name."""
        return self._plugin_context.get('package_name')

    @property
    def package_version(self):
        """The plugin package version."""
        return self._plugin_context.get('package_version')

    @property
    def prefix(self):
        """The plugin prefix."""
        return utils.internal.plugin_prefix(
            package_name=self.package_name,
            package_version=self.package_version,
            deployment_id=self._deployment_id,
            plugin_name=self.name,
            sys_prefix_fallback=True)

    @property
    def workdir(self):
        """The plugin workdir.

        This directory is unique for each (deployment, plugin) combination.

        Note: if this operation is executed not as part of a deployment or
        a plugin, None is returned.
        """
        if not self.name:
            return None
        workdir = self._endpoint.get_workdir()
        plugin_workdir = os.path.join(workdir, 'plugins', self.name)
        if not os.path.exists(plugin_workdir):
            try:
                os.makedirs(plugin_workdir)
            except IOError as e:
                if e.errno == errno.EEXIST:
                    pass
                else:
                    raise
        return plugin_workdir


class ImmutableProperties(dict):
    """
    Of course this is not actually immutable, but it is good enough to provide
    an API that will tell you you're doing something wrong if you try updating
    the static node properties in the normal way.
    """

    @staticmethod
    def _raise():
        raise exceptions.NonRecoverableError(
            'Cannot override read only properties')

    def __setitem__(self, key, value):
        self._raise()

    def __delitem__(self, key):
        self._raise()

    def update(self, E=None, **F):
        self._raise()

    def clear(self):
        self._raise()

    def pop(self, k, d=None):
        self._raise()

    def popitem(self):
        self._raise()
