########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

"""
Handles 'cfy install'
"""

import os
import errno
import urlparse

from cloudify_cli import utils
from cloudify_cli.commands import blueprints
from cloudify_cli.commands import executions
from cloudify_cli.commands import deployments
from cloudify_cli.exceptions import CloudifyCliError
from cloudify_cli.constants import DEFAULT_BLUEPRINT_PATH
from cloudify_cli.constants import DEFAULT_INSTALL_WORKFLOW
from cloudify_cli.constants import DEFAULT_BLUEPRINT_FILE_NAME
from cloudify_cli.constants import DEFAULT_INPUTS_PATH_FOR_INSTALL_COMMAND


def install(blueprint_path, blueprint_id, validate_blueprint, archive_location,
            blueprint_filename, deployment_id, inputs, workflow_id, parameters,
            allow_custom_parameters, timeout, include_logs,
            auto_generate_ids, json):

    # First, make sure the `blueprint_path` wasn't supplied with
    # `archive_location` or with `blueprint_filename`
    _check_for_mutually_exclusive_arguments(blueprint_path,
                                            archive_location,
                                            blueprint_filename)

    # The presence of the `archive_location` argument is used to distinguish
    # between `install` in 'blueprints upload' mode,
    # and `install` in 'blueprints publish archive' mode.
    if archive_location:
        blueprints.check_if_archive_type_is_supported(archive_location)

        if not blueprint_filename:
            blueprint_filename = DEFAULT_BLUEPRINT_FILE_NAME

        # If blueprint_id wasn't supplied, assign it to the name of the archive
        if not blueprint_id:
            (archive_location, archive_location_type) = \
                blueprints.determine_archive_type(archive_location)
            # if the archive is a local path, assign blueprint_id the name of
            # the archive file without the extension
            if archive_location_type == 'path':
                filename, ext = os.path.splitext(
                    os.path.basename(archive_location))
                blueprint_id = filename
            # if the archive is a url, assign blueprint_id name of the file
            # that the url leads to, without the extension.
            # e.g. http://example.com/path/archive.zip?para=val#sect -> archive
            elif archive_location_type == 'url':
                path = urlparse.urlparse(archive_location).path
                archive_file = path.split('/')[-1]
                archive_name = archive_file.split('.')[0]
                blueprint_id = archive_name
            else:
                raise CloudifyCliError("The archive's source is not a local "
                                       'file path nor a web url')

        # auto-generate blueprint id if necessary
        if _auto_generate_ids(auto_generate_ids):
            blueprint_id = _generate_suffixed_id(blueprint_id)

        blueprints.publish_archive(archive_location,
                                   blueprint_filename,
                                   blueprint_id)
    else:
        blueprint_path_supplied = bool(blueprint_path)
        if not blueprint_path:
            blueprint_path = os.path.join(utils.get_cwd(),
                                          DEFAULT_BLUEPRINT_PATH)

        # If blueprint_id wasn't supplied, assign it to the name of
        # folder containing the application's blueprint file.
        if not blueprint_id:
            blueprint_id = os.path.basename(
                os.path.dirname(
                    os.path.abspath(blueprint_path)))

        # Try opening `blueprint_path`, since `blueprints.upload` expects the
        # `blueprint_path` argument to be a file.
        # (The reason for this is beyond me. That's just the way it is)

        if _auto_generate_ids(auto_generate_ids):
            blueprint_id = _generate_suffixed_id(blueprint_id)

        try:
            with open(blueprint_path) as blueprint_file:
                blueprints.upload(blueprint_file,
                                  blueprint_id,
                                  validate_blueprint)
        except IOError as e:

            # No such file or directory
            if not blueprint_path_supplied and e.errno == errno.ENOENT:
                raise CloudifyCliError(
                    'Your blueprint was not found in the path: {0}.\n\n'
                    'Consider providing an explicit path to your blueprint '
                    'using the `-p`/`--blueprint-path` flag, like so:\n'
                    '`cfy install -p /path/to/blueprint_file.yaml`\n'
                    .format(blueprint_path)
                )
            else:
                raise CloudifyCliError(
                    'A problem was encountered while trying to open '
                    '{0}.\n({1})'.format(blueprint_path, e))

    # If deployment_id wasn't supplied, use the same name as the blueprint id.
    if not deployment_id:
        deployment_id = blueprint_id

    # generate deployment-id suffix if necessary
    if _auto_generate_ids(auto_generate_ids):
        deployment_id = _generate_suffixed_id(deployment_id)

    # If no inputs were supplied, and there is a file named inputs.yaml in
    # the cwd, use it as the inputs file
    if not inputs:
        if os.path.isfile(
            os.path.join(utils.get_cwd(),
                         DEFAULT_INPUTS_PATH_FOR_INSTALL_COMMAND)):

            inputs = DEFAULT_INPUTS_PATH_FOR_INSTALL_COMMAND

    deployments.create(blueprint_id,
                       deployment_id,
                       inputs)

    # although the `install` command does not need the `force` argument,
    # we *are* using the `executions start` handler as a part of it.
    # as a result, we need to provide it with a `force` argument, which is
    # defined below.
    force = False

    # if no workflow was supplied, execute the `install` workflow
    if not workflow_id:
        workflow_id = DEFAULT_INSTALL_WORKFLOW

    executions.start(workflow_id=workflow_id,
                     deployment_id=deployment_id,
                     timeout=timeout,
                     force=force,
                     allow_custom_parameters=allow_custom_parameters,
                     include_logs=include_logs,
                     parameters=parameters,
                     json=json)


def _check_for_mutually_exclusive_arguments(blueprint_path,
                                            archive_location,
                                            blueprint_filename):
    if blueprint_path and (archive_location or blueprint_filename):
        raise CloudifyCliError(
            "`-p/--blueprint-path` can't be supplied with "
            "`-l/--archive-location` and/or `-n/--blueprint-filename`"
        )


def _auto_generate_ids(auto_generate_ids):
    return utils.is_auto_generate_ids() or auto_generate_ids


def _generate_suffixed_id(id):
    return '{0}_{1}'.format(id, utils.generate_random_string())
