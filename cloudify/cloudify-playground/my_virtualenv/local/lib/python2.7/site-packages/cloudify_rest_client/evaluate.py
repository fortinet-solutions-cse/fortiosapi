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


class EvaluatedFunctions(dict):
    """
    Evaluated functions.
    """

    def __init__(self, evaluated_functions):
        self.update(evaluated_functions)

    @property
    def deployment_id(self):
        """
        :return: The deployment id this request belongs to.
        """
        return self['deployment_id']

    @property
    def payload(self):
        """
        :return: The evaluation payload.
        """
        return self['payload']


class EvaluateClient(object):

    def __init__(self, api):
        self.api = api

    def functions(self, deployment_id, context, payload):
        """Evaluate intrinsic functions in payload in respect to the
        provided context.

        :param deployment_id: The deployment's id of the node.
        :param context: The processing context
                        (dict with optional self, source, target).
        :param payload: The payload to process.
        :return: The payload with its intrinsic functions references
                 evaluated.
        :rtype: EvaluatedFunctions
        """
        assert deployment_id
        result = self.api.post('/evaluate/functions', data={
            'deployment_id': deployment_id,
            'context': context,
            'payload': payload
        })
        return EvaluatedFunctions(result)
