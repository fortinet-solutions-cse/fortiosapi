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
#Push image
openstack image show  "fgt54" > /dev/null 2>&1 || openstack image create --disk-format qcow2 --container-format bare  --public  "fgt54"  --file fortios.qcow2


#Create mgmt network for neutron for tenant VMs
neutron net-show left > /dev/null 2>&1 || neutron net-create left
neutron subnet-show left_subnet > /dev/null 2>&1 || neutron subnet-create left "10.40.40.0/24"  --name left_subnet  --host-route destination=10.20.20.0/24,nexthop=10.40.40.254 
#--gateway 10.40.40.254
neutron net-show right > /dev/null 2>&1 || neutron net-create right
neutron subnet-show right_subnet > /dev/null 2>&1 || neutron subnet-create right "10.20.20.0/24" --name right_subnet
#--gateway 10.20.20.254
 

if (nova show trafleft  > /dev/null 2>&1 );then
    echo "trafleft already installed"
else
    nova boot --image "Trusty x86_64" trafleft --key-name default --security-group default --flavor m1.small --user-data apache_userdata.txt --nic net-name=mgmt --nic net-name=left
    while [ $(nova list |grep trafleft | awk -F "|" '{print $4}') == "BUILD" ]; do
	sleep 4
    done
    
    FLOAT_IP="$(nova floating-ip-create | grep ext_net | awk -F "|" '{ print $3}')"
    nova floating-ip-associate trafleft $FLOAT_IP
fi

if (nova show trafright  > /dev/null 2>&1 );then
    echo "trafright already installed"
else
    nova boot --image "Trusty x86_64" trafright --key-name default --security-group default --flavor m1.small --user-data apache_userdata.txt --nic net-name=mgmt --nic net-name=right
    while [ $(nova list |grep trafright | awk -F "|" '{print $4}') == "BUILD" ]; do
	sleep 4
    done
    FLOAT_IP="$(nova floating-ip-create | grep ext_net | awk -F "|" '{ print $3}')"
    nova floating-ip-associate trafright $FLOAT_IP
fi


if (nova show fgt54  > /dev/null 2>&1 );then
    echo "fgt54 already installed"
else
    neutron port-show left1 > /dev/null 2>&1 ||neutron port-create left --port-security-enabled=False --fixed-ip ip_address=10.40.40.254 --name left1 
    neutron port-show right1 > /dev/null 2>&1 ||neutron port-create right --port-security-enabled=False --fixed-ip ip_address=10.20.20.254 --name right1 
    LEFTPORT=`neutron port-show left1 -F id -f value`
    RIGHTPORT=`neutron port-show right1 -F id -f value`
    nova boot --image "fgt54" fgt54 --config-drive=true --key-name default  --security-group default  --flavor m1.small  --user-data fgt-user-data.txt --nic net-name=mgmt --nic port-id=$LEFTPORT --nic port-id=$RIGHTPORT --file license=FGT.lic
    FLOAT_IP="$(nova floating-ip-create | grep ext_net | awk -F "|" '{ print $3}')"
    while [ $(nova list |grep fgt54 | awk -F "|" '{print $4}') == "BUILD" ]; do
	sleep 4
    done
    nova floating-ip-associate fgt54 $FLOAT_IP
fi
