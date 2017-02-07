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


EXECUTION_CANCELLED_RESULT = 'execution_cancelled'

cancel_request = False


def has_cancel_request():
    """
    Checks for requests to cancel the workflow execution.
    This should be used to allow graceful termination of workflow executions.

    If this method is not used and acted upon, a simple 'cancel'
    request for the execution will have no effect - 'force-cancel' will have
    to be used to abruptly terminate the execution instead.

    Note: When this method returns True, the workflow should make the
    appropriate cleanups and then it must raise an ExecutionCancelled error
    if the execution indeed gets cancelled (i.e. if it's too late to cancel
    there is no need to raise this exception and the workflow should end
    normally).

    :return: whether there was a request to cancel the workflow execution
    """
    return cancel_request


class ExecutionCancelled(Exception):
    """
    This exception should be raised when a workflow has been cancelled,
    once appropriate cleanups have taken place.
    """
    pass
