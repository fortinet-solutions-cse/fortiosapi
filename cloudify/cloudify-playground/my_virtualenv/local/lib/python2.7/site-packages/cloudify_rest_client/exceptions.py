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


class CloudifyClientError(Exception):

    def __init__(self, message, server_traceback=None,
                 status_code=-1, error_code=None):
        super(CloudifyClientError, self).__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.server_traceback = server_traceback

    def __str__(self):
        if self.status_code != -1:
            return '{0}: {1}'.format(self.status_code, self.message)
        return self.message


class DeploymentEnvironmentCreationInProgressError(CloudifyClientError):
    """
    Raised when there's attempt to execute a deployment workflow and
    deployment environment creation workflow execution is still running.
    In such a case, workflow execution should be retried after a reasonable
    time or after the execution of deployment environment creation workflow
    has terminated.
    """
    ERROR_CODE = 'deployment_environment_creation_in_progress_error'


class DeploymentEnvironmentCreationPendingError(CloudifyClientError):
    """
    Raised when there's attempt to execute a deployment workflow and
    deployment environment creation workflow execution is pending.
    In such a case, workflow execution should be retried after a reasonable
    time or after the execution of deployment environment creation workflow
    has terminated.
    """
    ERROR_CODE = 'deployment_environment_creation_pending_error'


class IllegalExecutionParametersError(CloudifyClientError):
    """
    Raised when an attempt to execute a workflow with wrong/missing parameters
    has been made.
    """
    ERROR_CODE = 'illegal_execution_parameters_error'


class NoSuchIncludeFieldError(CloudifyClientError):
    """
    Raised when an _include query parameter contains a field which does not
    exist for the queried data model.
    """
    ERROR_CODE = 'no_such_include_field_error'


class MissingRequiredDeploymentInputError(CloudifyClientError):
    """
    Raised when a required deployment input was not specified on deployment
    creation.
    """
    ERROR_CODE = 'missing_required_deployment_input_error'


class UnknownDeploymentInputError(CloudifyClientError):
    """
    Raised when an unexpected input was specified on deployment creation.
    """
    ERROR_CODE = 'unknown_deployment_input_error'


class FunctionsEvaluationError(CloudifyClientError):
    """
    Raised when function evaluation failed.
    """
    ERROR_CODE = 'functions_evaluation_error'


class UnknownModificationStageError(CloudifyClientError):
    """
    Raised when an unknown modification stage was provided.
    """
    ERROR_CODE = 'unknown_modification_stage_error'


class ExistingStartedDeploymentModificationError(CloudifyClientError):
    """
    Raised when a deployment modification start is attempted while another
    deployment modification is currently started
    """
    ERROR_CODE = 'existing_started_deployment_modification_error'


class DeploymentModificationAlreadyEndedError(CloudifyClientError):
    """
    Raised when a deployment modification finish/rollback is attempted on
    a deployment modification that has already been finished/rolledback
    """
    ERROR_CODE = 'deployment_modification_already_ended_error'


class UserUnauthorizedError(CloudifyClientError):
    """
    Raised when a call has been made to a secured resource with an
    unauthorized user (no credentials / bad credentials)
    """
    ERROR_CODE = 'unauthorized_error'


class PluginInUseError(CloudifyClientError):
    """
    Raised if a central deployment agent plugin deletion is attempted and at
    least one deployment is currently using this plugin.
    """
    ERROR_CODE = 'plugin_in_use'


class PluginInstallationError(CloudifyClientError):
    """
    Raised if a central deployment agent plugin installation fails.
    """
    ERROR_CODE = 'plugin_installation_error'


class PluginInstallationTimeout(CloudifyClientError):
    """
    Raised if a central deployment agent plugin installation times out.
    """
    ERROR_CODE = 'plugin_installation_timeout'


class MaintenanceModeActiveError(CloudifyClientError):
    """
    Raised when a call has been blocked due to maintenance mode being active.
    """
    ERROR_CODE = 'maintenance_mode_active'

    def __str__(self):
        return self.message


class MaintenanceModeActivatingError(CloudifyClientError):
    """
    Raised when a call has been blocked while maintenance mode is activating.
    """
    ERROR_CODE = 'entering_maintenance_mode'

    def __str__(self):
        return self.message


class NotModifiedError(CloudifyClientError):
    """
    Raised when a 304 not modified error was returned
    """
    ERROR_CODE = 'not_modified'

    def __str__(self):
        return self.message


class InvalidExecutionUpdateStatus(CloudifyClientError):
    """
    Raised when execution update failed do to invalid status update
    """
    ERROR_CODE = 'invalid_exception_status_update'


ERROR_MAPPING = dict([
    (error.ERROR_CODE, error)
    for error in [
        DeploymentEnvironmentCreationInProgressError,
        DeploymentEnvironmentCreationPendingError,
        IllegalExecutionParametersError,
        NoSuchIncludeFieldError,
        MissingRequiredDeploymentInputError,
        UnknownDeploymentInputError,
        FunctionsEvaluationError,
        UnknownModificationStageError,
        ExistingStartedDeploymentModificationError,
        DeploymentModificationAlreadyEndedError,
        UserUnauthorizedError,
        MaintenanceModeActiveError,
        MaintenanceModeActivatingError,
        NotModifiedError,
        InvalidExecutionUpdateStatus,
        PluginInUseError,
        PluginInstallationError,
        PluginInstallationTimeout]])
