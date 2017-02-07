########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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
Handles all commands that start with 'cfy events'
"""

from cloudify_cli import utils
from cloudify_cli.exceptions import CloudifyCliError, \
    SuppressedCloudifyCliError
from cloudify_cli.logger import get_logger, get_events_logger
from cloudify_rest_client.exceptions import CloudifyClientError
from cloudify_cli.execution_events_fetcher import ExecutionEventsFetcher, \
    wait_for_execution


def ls(execution_id, include_logs, tail, json):
    logger = get_logger()
    management_ip = utils.get_management_server_ip()
    logger.info('Listing events for execution id {0} '
                '[include_logs={1}]'.format(execution_id, include_logs))
    client = utils.get_rest_client(management_ip)
    try:
        execution_events = ExecutionEventsFetcher(
            client,
            execution_id,
            include_logs=include_logs)

        events_logger = get_events_logger(json)

        if tail:
            execution = wait_for_execution(client,
                                           client.executions.get(execution_id),
                                           events_handler=events_logger,
                                           include_logs=include_logs,
                                           timeout=None)   # don't timeout ever
            if execution.error:
                logger.info('Execution of workflow {0} for deployment '
                            '{1} failed. [error={2}]'.format(
                                execution.workflow_id,
                                execution.deployment_id,
                                execution.error))
                raise SuppressedCloudifyCliError()
            else:
                logger.info('Finished executing workflow {0} on deployment '
                            '{1}'.format(
                                execution.workflow_id,
                                execution.deployment_id))
        else:
            # don't tail, get only the events created until now and return
            events = execution_events.fetch_and_process_events(
                events_handler=events_logger)
            logger.info('\nTotal events: {0}'.format(events))
    except CloudifyClientError as e:
        if e.status_code != 404:
            raise
        raise CloudifyCliError('Execution {0} not found'.format(execution_id))
