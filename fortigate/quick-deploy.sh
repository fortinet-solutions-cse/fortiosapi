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

set -e

. /nova.rc

#Push image
openstack image show  "FGT VM64 1100" > /dev/null 2>&1 || openstack image create --disk-format qcow2 --container-format bare  --public  "FGT VM64 1100"  --file fortios.qcow2

#Tried (ref http://docs.openstack.org/cli-reference/nova.html)

nova show FGT1  > /dev/null 2>&1 || nova boot --image "FGT VM64 1100" FGT1 --key-name default --security-group default --flavor m1.small --user-data fgt-user-data.txt --config-drive=true --file license=FGVMUL0000075926.lic --nic net-name=private

#IP=nova floating-ip-create

#nova floating-ip-associate FGT1 10.10.11.15
#sudo iptables -t nat -A PREROUTING -p tcp --dport 4043 -j DNAT --to-destination 10.10.11.15:443
#sudo iptables -t nat -A PREROUTING -p tcp --dport 4022 -j DNAT --to-destination 10.10.11.15:22
