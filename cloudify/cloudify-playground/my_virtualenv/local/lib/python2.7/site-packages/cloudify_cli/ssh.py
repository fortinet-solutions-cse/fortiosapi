import os

import fabric.api as fab


from cloudify_cli.cli import get_global_verbosity
from cloudify_cli import utils
from cloudify_cli.exceptions import CloudifyCliError


def get_manager_date():
    # output here should be hidden anyway.
    with fab.settings(fab.hide('running', 'stdout')):
        return run_command_on_manager('date +%Y%m%dT%H%M%S').stdout


def get_file_from_manager(remote_source_path, destination_path):
    key_filename = os.path.expanduser(utils.get_management_key())
    with fab.settings(
            fab.hide('running', 'stdout'),
            host_string=utils.build_manager_host_string(),
            key_filename=key_filename):
        fab.get(remote_source_path, destination_path)


def put_file_in_manager(source_path,
                        remote_source_path,
                        use_sudo=True,
                        key_filename=None,
                        user=None):
    if not key_filename:
        key_filename = os.path.expanduser(utils.get_management_key())
    with fab.settings(
            fab.hide('running', 'stdout'),
            host_string=utils.build_manager_host_string(user=user),
            key_filename=key_filename):
        fab.put(use_sudo=use_sudo,
                local_path=source_path,
                remote_path=remote_source_path)


def run_command_on_manager(command,
                           use_sudo=False,
                           open_shell=False,
                           host_string='',
                           force_output=False):
    """Runs an SSH command on a Manager.

    `open_shell` opens an interactive shell to the server.
    `host_string` can be explicitly provided to save on REST calls.
    `force_output` forces all output as if running in verbose.
    """
    host_string = host_string or utils.build_manager_host_string()

    def execute():
        key_filename = os.path.expanduser(utils.get_management_key())
        with fab.settings(
                host_string=host_string,
                key_filename=key_filename,
                warn_only=True):
            if use_sudo:
                output = fab.sudo(command)
            elif open_shell:
                fab.open_shell(command)
                return None
            else:
                output = fab.run(command)
            if output.failed:
                raise CloudifyCliError(
                    'Failed to execute: {0} ({1})'.format(
                        output.real_command, output.stderr))
            return output

    if get_global_verbosity() or force_output:
        return execute()
    else:
        with fab.hide('running', 'stdout', 'stderr', 'warnings'):
            return execute()
