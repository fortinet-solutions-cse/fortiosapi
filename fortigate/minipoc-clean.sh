#!/bin/bash

# #######
# Copyright (c) 2016 Fortinet All rights reserved
# Author: Nicolas Thomas nthomas_at_fortinet.com
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

set -x

#if nova access not set then get them from nova.rc
if [ -x "$OS_AUTH_URL" ]; then 
  echo "get the Openstack access from ~/nova.rc"
  . ~/nova.rc
fi



nova delete trafleft
nova delete trafright
nova delete fgt54


neutron port-delete left1
neutron port-delete right1
neutron net-delete left
neutron net-delete right
