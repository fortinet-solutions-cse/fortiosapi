#!/bin/python

import fabric.api
from fabric.contrib.files import exists as remote_exists

from cloudify import ctx


def retrieve(agent_packages):
    ctx.logger.info('Downloading Cloudify Agents...')

    for agent, source in agent_packages.items():
        # if source is not a downloadable link, it will not be downloaded
        if not source.startswith(('http', 'https', 'ftp')):
            continue

        dest_path = ctx.instance.runtime_properties['agent_packages_path']
        agent_name = agent.replace('_', '-')

        # This is a workaround for mapping Centos release names to versions
        # to provide a better UX when providing agent inputs.
        if agent_name == 'centos-7x-agent':
            agent_name = 'centos-core-agent'
        elif agent_name == 'centos-6x-agent':
            agent_name = 'centos-final-agent'
        elif agent_name == 'redhat-7x-agent':
            agent_name = 'redhat-maipo-agent'
        elif agent_name == 'redhat-6x-agent':
            agent_name = 'redhat-santiago-agent'

        if agent_name == 'cloudify-windows-agent':
            filename = '{0}.exe'.format(agent_name)
        else:
            filename = '{0}.tar.gz'.format(agent_name)
        dest_file = '{0}/{1}'.format(dest_path, filename)

        ctx.logger.info('Downloading Agent Package {0} to {1} if it does not '
                        'already exist...'.format(source, dest_file))
        if remote_exists(dest_file):
            ctx.logger.info('agent package file will be '
                            'overridden: {0}'.format(dest_file))
        dl_cmd = 'curl --retry 10 -f -s -S -L {0} --create-dirs -o {1}'
        fabric.api.sudo(dl_cmd.format(source, dest_file))
