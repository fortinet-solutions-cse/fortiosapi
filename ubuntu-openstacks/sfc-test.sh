#!/bin/bash -xe
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


# this create 2 networks, 2 machines a fortigate in the middle and propagate routes so that traffic can be done (there is apache2 on both)
# do not put the fortigate as the default gateway on the networks it is not supported by openstack

#if nova access not set then get them from nova.rc
if [ -x "$OS_AUTH_URL" ]; then 
  echo "get the Openstack access from ~/nova.rc"
  . ~/nova.rc
fi

#Create mgmt network for neutron for tenant VMs
neutron net-show net1 > /dev/null 2>&1 || neutron net-create net1 --provider:network_type vxlan
neutron subnet-show net1_subnet > /dev/null 2>&1 || neutron subnet-create net1 "192.168.1.0/23"  --name net1_subnet  

for i in `seq 1 6`
do
    neutron port-create  net1 --port-security-enabled=False  --name p$i 
done

for vi in `seq 1 3`
do
    pl=`echo "$vi*2-1"|bc`
    pr=`echo "$vi*2"|bc`
    LEFTPORT=`neutron port-show p$pl -F id -f value`
    RIGHTPORT=`neutron port-show p$pr -F id -f value`
    nova boot --image "Cirros 0.3.4" vm$vi --key-name default  --security-group default  --flavor m1.small   --nic port-id=$LEFTPORT --nic port-id=$RIGHTPORT
done

 
    neutron port-pair-create   --description "Firewall SF instance 1"   --ingress p1   --egress p2 PP1
    neutron port-pair-create   --description "Firewall SF instance 2"   --ingress p3   --egress p4 PP2
    neutron port-pair-create   --description "IDS SF instance"   --ingress p5   --egress p6 PP3
    neutron port-pair-group-create   --port-pair PP1 --port-pair PP2 PPG1
    neutron port-pair-group-create   --port-pair PP3 PPG2
    neutron port-chain-create   --port-pair-group PPG1 --port-pair-group PPG2   --flow-classifier FC1 PC1
