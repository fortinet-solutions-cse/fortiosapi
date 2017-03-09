#!/bin/bash -x

lxc launch ubuntu:16.04 cloudify

#Follow http://docs.getcloudify.org/3.4.1/


LXC="lxc exec cloudify -- "
$LXC ping -c 4 getcloudify.org
$LXC apt -y install python-pip python-virtualenv wget git
$LXC pip install --upgrade pip
$LXC mkdir -p /root/.ssh
$LXC wget -c http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/get-cloudify.py
$LXC python get-cloudify.py --upgrade
# check this https://groups.google.com/forum/#!topic/cloudify-users/U1xMdkZ0HqM
lxc file push ~/.ssh/id_rsa* cloudify/root/.ssh/

#  git -C cloudify-openstack-plugin/ checkout tags/2.0

lxc launch images:centos/7/amd64 cfy-mngr

# Create a centos container and access to put cfy mngr there
#Follow http://docs.getcloudify.org/3.4.1/cli/bootstrap/

LXCm="lxc exec cfy-mngr -- "
$LXCm ping -c 4 getcloudify.org
$LXCm yum update
$LXCm yum -y install openssh-server anacron gcc python-devel sudo 
$LXCm mkdir -p /root/.ssh
# check this https://groups.google.com/forum/#!topic/cloudify-users/U1xMdkZ0HqM
lxc file push ~/.ssh/id_rsa.pub cfy-mngr/root/.ssh/authorized_keys
$LXCm chown root:root /root/.ssh/authorized_keys
$LXCm echo -e "fortinet\nfortinet" | passwd

