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

from dsl_parser.interfaces.operation_merger import OperationMerger


class InterfaceMerger(object):

    def __init__(self,
                 overriding_interface,
                 overridden_interface,
                 operation_merger=OperationMerger):

        self.overriding_interface = overriding_interface
        self.overridden_interface = overridden_interface
        self.operation_merger = operation_merger

    def merge(self):

        merged_interface = {}

        for overridden_operation_name, overridden_operation \
                in self.overridden_interface.items():

            overriding_operation = self.overriding_interface.get(
                overridden_operation_name,
                None)

            merger = self.operation_merger(
                overriding_operation=overriding_operation,
                overridden_operation=overridden_operation
            )
            merged_operation = merger.merge()
            merged_interface[overridden_operation_name] = merged_operation

        for overriding_operation_name, overriding_operation \
                in self.overriding_interface.items():

            overridden_operation = self.overridden_interface.get(
                overriding_operation_name,
                None)

            merger = self.operation_merger(
                overriding_operation=overriding_operation,
                overridden_operation=overridden_operation
            )
            merged_operation = merger.merge()
            merged_interface[overriding_operation_name] = merged_operation

        return merged_interface


class InterfacesMerger(object):

    def __init__(self,
                 overriding_interfaces,
                 overridden_interfaces,
                 operation_merger):

        self.overriding_interfaces = overriding_interfaces
        self.overridden_interfaces = overridden_interfaces
        self.operation_merger = operation_merger
        self.interface_merger = InterfaceMerger

    def merge(self):

        merged_interfaces = {}

        for overridden_interface_name, overridden_interface \
                in self.overridden_interfaces.items():

            overriding_interface = self.overriding_interfaces.get(
                overridden_interface_name, {})

            interface_merger = self.interface_merger(
                overriding_interface=overriding_interface,
                overridden_interface=overridden_interface,
                operation_merger=self.operation_merger
            )
            merged_interface = interface_merger.merge()
            merged_interfaces[overridden_interface_name] = merged_interface

        for overriding_interface_name, overriding_interface \
                in self.overriding_interfaces.items():

            overridden_interface = self.overridden_interfaces.get(
                overriding_interface_name, {})

            interface_merger = self.interface_merger(
                overriding_interface=overriding_interface,
                overridden_interface=overridden_interface,
                operation_merger=self.operation_merger
            )
            merged_interface = interface_merger.merge()
            merged_interfaces[overriding_interface_name] = merged_interface

        return merged_interfaces
