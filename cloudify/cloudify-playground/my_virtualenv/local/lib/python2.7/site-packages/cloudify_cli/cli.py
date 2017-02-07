########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############

import sys
import logging
import argparse
import StringIO
import traceback
from itertools import imap

import argcomplete

from cloudify import logs
from cloudify_rest_client.exceptions import NotModifiedError
from cloudify_rest_client.exceptions import CloudifyClientError
from cloudify_rest_client.exceptions import MaintenanceModeActiveError
from cloudify_rest_client.exceptions import MaintenanceModeActivatingError

from cloudify_cli import constants
from cloudify_cli.exceptions import CloudifyBootstrapError
from cloudify_cli.exceptions import SuppressedCloudifyCliError


HIGH_VERBOSE = 3
MEDIUM_VERBOSE = 2
LOW_VERBOSE = 1
NO_VERBOSE = 0

verbosity_level = NO_VERBOSE


def main():
    _configure_loggers()
    _set_cli_except_hook()
    args = _parse_args(sys.argv[1:])
    args.handler(args)


def _parse_args(args):
    """
    Parses the arguments using the Python argparse library.
    Generates shell autocomplete using the argcomplete library.

    :param list args: arguments from cli
    :rtype: `python argument parser`
    """

    parser = register_commands()
    argcomplete.autocomplete(parser)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    parsed = parser.parse_args(args)
    if parsed.debug:
        global_verbosity_level = HIGH_VERBOSE
    else:
        global_verbosity_level = parsed.verbosity
    set_global_verbosity_level(global_verbosity_level)
    if global_verbosity_level >= HIGH_VERBOSE:
        set_debug()
    return parsed


def register_commands():
    from cloudify_cli.config.parser_config import parser_config
    parser_conf = parser_config()
    parser = argparse.ArgumentParser(description=parser_conf['description'])

    # Direct arguments for the 'cfy' command (like -v)
    for argument_name, argument in parser_conf['arguments'].iteritems():
        parser.add_argument(argument_name, **argument)

    subparsers = parser.add_subparsers(
        title='Commands',
        metavar=''
    )

    for command_name, command in parser_conf['commands'].iteritems():

        if 'sub_commands' in command:

            # Add sub commands. Such as 'cfy blueprints list',
            # 'cfy deployments create' ...
            controller_help = command['help']
            controller_parser = subparsers.add_parser(
                command_name, help=controller_help
            )
            controller_subparsers = controller_parser.add_subparsers(
                title='Commands',
                metavar=(' ' *
                         (constants.HELP_TEXT_COLUMN_BUFFER +
                          longest_command_length(command['sub_commands'])))
            )
            for controller_sub_command_name, controller_sub_command in \
                    command['sub_commands'].iteritems():
                register_command(controller_subparsers,
                                 controller_sub_command_name,
                                 controller_sub_command)
        else:

            # Add direct commands. Such as 'cfy status', 'cfy ssh' ...
            register_command(subparsers, command_name, command)

    return parser


def _register_argument(args, command_parser):
    command_arg_names = []

    for argument_name, argument in args.iteritems():
        completer = argument.get('completer')
        if completer:
            del argument['completer']

        arg = command_parser.add_argument(
                *argument_name.split(','),
                **argument
        )

        if completer:
            arg.completer = completer

        command_arg_names.append(argument['dest'])

    return command_arg_names


def register_command(subparsers, command_name, command):

    command_help = command['help']
    command_parser = subparsers.add_parser(
        command_name, help=command_help,
        formatter_class=ConciseArgumentDefaultsHelpFormatter
    )

    command_arg_names = []
    arguments = command.get('arguments', {})

    mutually_exclusive = arguments.pop('_mutually_exclusive', [])

    command_arg_names += _register_argument(arguments,
                                            command_parser)

    for mutual_exclusive_group in mutually_exclusive:
        command_arg_names += _register_argument(
                mutual_exclusive_group,
                command_parser.add_mutually_exclusive_group(required=True)
        )
    # Add verbosity flag for each command
    command_parser.add_argument(
        '-v', '--verbose',
        dest='verbosity',
        action='count',
        default=NO_VERBOSE,
        help='Set verbosity level (can be passed multiple times)'
    )

    # Add debug flag for each command
    command_parser.add_argument(
        '--debug',
        dest='debug',
        action='store_true',
        help='Set debug output (equivalent to -vvv)'
    )

    def command_cmd_handler(args):
        kwargs = {}
        for arg_name in command_arg_names:
            # Filter verbosity since it accessed globally
            # and not via the method signature.
            if hasattr(args, arg_name):
                arg_value = getattr(args, arg_name)
                kwargs[arg_name] = arg_value

        command['handler'](**kwargs)

    command_parser.set_defaults(handler=command_cmd_handler)


def set_global_verbosity_level(verbose):
    """
    Sets the global verbosity level.

    :param bool verbose: verbose output or not.
    """
    global verbosity_level
    verbosity_level = verbose
    logs.EVENT_VERBOSITY_LEVEL = verbose


def set_debug():
    """
    Sets all previously configured
    loggers to debug level

    """
    from cloudify_cli.logger import all_loggers
    for logger_name in all_loggers():
        logging.getLogger(logger_name).setLevel(logging.DEBUG)


def get_global_verbosity():
    """
    Returns the globally set verbosity

    :return: verbose or not
    :rtype: bool
    """
    global verbosity_level
    return verbosity_level


def _configure_loggers():
    from cloudify_cli import logger
    logger.configure_loggers()


def _set_cli_except_hook():

    def recommend(possible_solutions):

        from cloudify_cli.logger import get_logger
        logger = get_logger()

        logger.info('Possible solutions:')
        for solution in possible_solutions:
            logger.info('  - {0}'.format(solution))

    def new_excepthook(tpe, value, tb):

        from cloudify_cli.logger import get_logger
        logger = get_logger()

        prefix = None
        server_traceback = None
        output_message = True
        if issubclass(tpe, CloudifyClientError):
            server_traceback = value.server_traceback
            if not issubclass(
                    tpe,
                    (MaintenanceModeActiveError,
                     MaintenanceModeActivatingError,
                     NotModifiedError)):
                # this means we made a server call and it failed.
                # we should include this information in the error
                prefix = 'An error occurred on the server'
        if issubclass(tpe, SuppressedCloudifyCliError):
            output_message = False
        if issubclass(tpe, CloudifyBootstrapError):
            output_message = False
        if verbosity_level:
            # print traceback if verbose
            s_traceback = StringIO.StringIO()
            traceback.print_exception(
                etype=tpe,
                value=value,
                tb=tb,
                file=s_traceback)
            logger.error(s_traceback.getvalue())
            if server_traceback:
                logger.error('Server Traceback (most recent call last):')

                # No need for print_tb since this exception
                # is already formatted by the server
                logger.error(server_traceback)
        if output_message and not verbosity_level:

            # if we output the traceback
            # we output the message too.
            # print_exception does that.
            # here we just want the message (non verbose)
            if prefix:
                logger.error('{0}: {1}'.format(prefix, value))
            else:
                logger.error(value)
        if hasattr(value, 'possible_solutions'):
            recommend(getattr(value, 'possible_solutions'))

    sys.excepthook = new_excepthook


def longest_command_length(commands_dict):
    return max(imap(len, commands_dict))


class ConciseArgumentDefaultsHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter):

    def _get_help_string(self, action):

        default = action.default
        help = action.help

        if default != argparse.SUPPRESS and default not in [None, False]:
            if '%(default)' not in help:
                help += ' (default: %(default)s)'

        return help


if __name__ == '__main__':
    main()
