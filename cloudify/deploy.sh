#!/bin/bash -x

lxc launch images:centos/7/amd64 cfy-manager

#Follow http://docs.getcloudify.org/3.4.0/cli/bootstrap/

sleep 24

LXC="lxc exec cfy-manager"
$LXC yum update
$LXC -- yum -y install openssh-server anacron gcc python-devel sudo 
$LXC mkdir -p /root/.ssh
$LXC 


# check this https://groups.google.com/forum/#!topic/cloudify-users/U1xMdkZ0HqM
lxc file push ~/.ssh/id_rsa.pub cfy-manager/root/.ssh/authorized_keys
