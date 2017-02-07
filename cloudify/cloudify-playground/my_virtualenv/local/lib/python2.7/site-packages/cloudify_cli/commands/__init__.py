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

# ignore flake because its not happy
# we are importing stuff and not using them.
# but we actually are using them from other files

# flake8: noqa

from cloudify_cli.commands import dev as dev_module
from cloudify_cli.commands import install as install_module

# import cfy actions
from cloudify_cli.commands.version import VersionAction as version

# import cfy direct commands
from cloudify_cli.commands.install import install
from cloudify_cli.commands.uninstall import uninstall
from cloudify_cli.commands.dev import dev
from cloudify_cli.commands.bootstrap import bootstrap
from cloudify_cli.commands.teardown import teardown
from cloudify_cli.commands.status import status
from cloudify_cli.commands.use import use
from cloudify_cli.commands.ssh import ssh
from cloudify_cli.commands.init import init
from cloudify_cli.commands.recover import recover

# import cfy sub commands
from cloudify_cli.commands import plugins
from cloudify_cli.commands import blueprints
from cloudify_cli.commands import snapshots
from cloudify_cli.commands import agents
from cloudify_cli.commands import deployments
from cloudify_cli.commands import events
from cloudify_cli.commands import executions
from cloudify_cli.commands import nodes
from cloudify_cli.commands import node_instances
from cloudify_cli.commands import workflows
from cloudify_cli.commands import local
from cloudify_cli.commands import logs
from cloudify_cli.commands import upgrade
from cloudify_cli.commands import rollback
from cloudify_cli.commands import maintenance
from cloudify_cli.commands import groups
