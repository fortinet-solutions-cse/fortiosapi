#!/bin/bash -xe

#Follow http://docs.getcloudify.org/3.4.1/
export LC_ALL=C

sudo apt -y install python-pip python-virtualenv wget git
sudo pip install --upgrade pip
wget -c http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/get-cloudify.py
python get-cloudify.py -e cfy_virtualenv --install-virtualenv --upgrade

#  git -C cloudify-openstack-plugin/ checkout tags/2.0
[ -d cloudify-manager-blueprints ] ||git clone https://github.com/cloudify-cosmo/cloudify-manager-blueprints.git
git -C cloudify-manager-blueprints/ checkout tags/3.4.1

lxc launch images:centos/7/amd64 cfy-mngr && sleep 12
# Create a centos container and access to put cfy mngr there
#Follow http://docs.getcloudify.org/3.4.1/cli/bootstrap/

LXCm="lxc exec cfy-mngr -- "
$LXCm ping -c 4 getcloudify.org
$LXCm yum update
$LXCm yum -y install openssh-server anacron gcc python-devel sudo wget which java
$LXCm mkdir -p /root/.ssh
# check this https://groups.google.com/forum/#!topic/cloudify-users/U1xMdkZ0HqM
lxc file push ~/.ssh/id_rsa.pub cfy-mngr/root/.ssh/authorized_keys
$LXCm chown root:root /root/.ssh/authorized_keys
echo -e "fortinet\nfortinet" | $LXCm passwd
echo 'export JAVACMD=`which java`' | $LXCm tee -a /etc/environment
$LXCm sudo reboot
sleep 5
$LXCm ping -c 4 getcloudify.org
export LXCmIP=`lxc exec cfy-mngr -- ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1`
ssh-keyscan $LXCmIP >> $HOME/.ssh/known_hosts

envsubst < cfy-lxc-mngr.template >  lxc-manager-blueprint-inputs.yaml

source cfy_virtualenv/bin/activate
cfy init -r
cfy bootstrap --install-plugins -p cloudify-manager-blueprints/simple-manager-blueprint.yaml -i lxc-manager-blueprint-inputs.yaml
#Ref : http://docs.getcloudify.org/3.4.1/plugins/openstack/
. ~/nova.rc
envsubst < openstack_config.template | $LXCm tee /root/openstack_config.json
cfy use -t $LXCmIP
cfy status

cat <<EOF
To use cloudify run:
source cfy_virtualenv/bin/activate
cfy use -t $LXCmIP

Then cfy cli is fonctionnal see http://docs.getcloudify.org/3.4.1/cli/overview/
Or log with admin/fortinet to http://$LXCmIP
EOF
