#!/bin/bash -xe

#Follow http://docs.getcloudify.org/3.4.1/
export LC_ALL=C

sudo apt -y install python-pip python-virtualenv wget git
#sudo pip install --upgrade pip
wget -c http://repository.cloudifysource.org/cloudify/4.0.0/ga-release/cloudify_4.0.0~ga_amd64.deb                                           
sudo dpkg -i cloudify*.deb

lxc launch images:centos/7/amd64 cfy-mngr && sleep 12
# Create a centos container and access to put cfy mngr there
#Follow http://docs.getcloudify.org/3.4.1/cli/bootstrap/

LXCm="lxc exec cfy-mngr -- "
$LXCm ping -c 4 github.com
$LXCm yum -y update
$LXCm yum -y install openssh-server anacron gcc python-devel sudo wget which java
$LXCm mkdir -p /root/.ssh
# check this https://groups.google.com/forum/#!topic/cloudify-users/U1xMdkZ0HqM
lxc file push ~/.ssh/id_rsa.pub cfy-mngr/root/.ssh/authorized_keys
lxc file push ~/.ssh/id_rsa cfy-mngr/root/
$LXCm chown root:root /root/.ssh/authorized_keys
echo -e "fortinet\nfortinet" | $LXCm passwd
JAVACMD=`$LXCm which java`
echo "export JAVACMD=$JAVACMD" | $LXCm tee -a /etc/environment
$LXCm sudo reboot
sleep 5
$LXCm ping -c 4 github.com
export LXCmIP=`lxc exec cfy-mngr -- ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1`
ssh-keyscan $LXCmIP >> $HOME/.ssh/known_hosts

envsubst < cfy-lxc-mngr.template >  lxc-manager-blueprint-inputs.yaml

cfy init -r
cfy bootstrap --install-plugins /opt/cfy/cloudify-manager-blueprints/simple-manager-blueprint.yaml -i lxc-manager-blueprint-inputs.yaml
#--task-retry-interval 15 --task-retries 3  --keep-up-on-failure
    #|| echo "error catched but keep going anyway"
#Ref : http://docs.getcloudify.org/3.4.1/plugins/openstack/
. ~/nova.rc
envsubst < openstack_config.template | $LXCm tee /root/openstack_config.json
cfy init -r
cfy profiles use $LXCmIP -u admin -p fortinet -t default_tenant 
cfy status

cat <<EOF
To use cloudify run:
Then cfy cli is fonctionnal see http://docs.getcloudify.org/3.4.1/cli/overview/
log with admin/fortinet to http://$LXCmIP
For completion run: eval "$(_CFY_COMPLETE=source cfy)"   
EOF
