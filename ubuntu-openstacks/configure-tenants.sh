#!/bin/bash -ex
#
#    fortinet-configure-openstack
#    Copyright (C) 2016 Fortinet  Ltd.
#
#    Authors: Nicolas Thomss  <nthomasfortinet.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


. ~/nova.rc
echo "This script create 2 tenants /mgmt networks and routers relies on configure-openstack being run before"

NEUTRON_EXT_NET_GW="10.10.10.1"
NEUTRON_EXT_NET_CIDR="10.10.10.0/23"

NEUTRON_EXT_NET_NAME="ext_net" # Unused
NEUTRON_DNS=$NEUTRON_EXT_NET_GW
NEUTRON_FLOAT_RANGE_START="10.10.11.12"
NEUTRON_FLOAT_RANGE_END="10.10.11.253"

NEUTRON_FIXED_NET_CIDR="192.168.16.0/22"


#create projects/users/role
for i in 1 2
do
    source ~/nova.rc
    openstack project create --description "Fortinet min-poc $i project" mini-poc$i
    openstack user create --project mini-poc$i --password fortinet tenant$i
    openstack role add --user  tenant$i --project mini-poc$i  Member

    echo "unset SERVICE_TOKEN
unset SERVICE_ENDPOINT 
export OS_AUTH_URL=$OS_AUTH_URL
export OS_USERNAME=tenant$i
export OS_PASSWORD=fortinet
export OS_TENANT_NAME=tenant$i
export OS_REGION_NAME=$OS_REGION_NAME
export OS_PROJECT_NAME=mini-poc$i
" > ~/tenant$i.rc

    source ~/tenant$i.rc
        
    echo "Configuring Openstack Neutron Networking"

    #Create mgmt network for neutron for tenant VMs
    neutron net-show mgmt$i > /dev/null 2>&1 || neutron net-create mgmt$i
    neutron subnet-show mgmt$i_subnet > /dev/null 2>&1 || neutron subnet-create mgmt$i $NEUTRON_FIXED_NET_CIDR -- --name mgmt$i_subnet --dns_nameservers list=true $NEUTRON_DNS
    SUBNET_ID=$(neutron subnet-show mgmt$i_subnet | grep " id" | awk '{print $4}')

    #Create router for external network and mgmt network
    neutron router-show tenant$i-router > /dev/null 2>&1 || neutron router-create tenant$i-router
    ROUTER_ID=`neutron router-show tenant$i-router -f value --field id`
    EXTERNAL_NETWORK_ID=$(neutron net-show ext_net | grep " id" | awk '{print $4}')

    neutron router-gateway-clear tenant$i-router || true
    neutron router-gateway-set $ROUTER_ID $EXTERNAL_NETWORK_ID
    ## make it always ok to have it indempodent.
    neutron router-interface-add $ROUTER_ID $SUBNET_ID || true



    #Configure the default security group to allow ICMP and SSH
    openstack security group rule create --proto icmp default || echo "should have been created already"
    openstack security group rule create --proto tcp --dst-port 22 default || echo "should have been created already"
    openstack security group rule create --proto tcp --dst-port 80 default || echo "should have been created already"
    openstack security group rule create --proto tcp --dst-port 443 default || echo "should have been created already"
    #port for RDP
    openstack security group rule create --proto tcp --dst-port 3389 default || echo "should have been created already"


    ##make wide open
    openstack security group rule create --proto tcp --dst-port 1:65535  default || echo "should have been created already"
    openstack security group rule create --proto udp --dst-port 1:65535  default || echo "should have been created already"


    #Upload a default SSH key
    openstack keypair create  --public-key ~/.ssh/id_rsa.pub default  || echo "asssuming key is already uploaded"

done
