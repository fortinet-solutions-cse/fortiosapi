#!/bin/bash -e

uname -a

# update system
# yum update --skip-broken -y

# install requirements for python-lxml
sudo yum install libxslt libxml2 -y

status=`systemctl status firewalld | grep "Active:"| awk '{print $2}'`

if [ "z$status" == 'zactive' ]; then
    # add http(s) rules
    sudo firewall-cmd --zone=public --add-port=80/tcp --permanent
    sudo firewall-cmd --zone=public --add-port=443/tcp --permanent
    # add influxdb connection
    sudo firewall-cmd --zone=public --add-port=8086/tcp --permanent
    # port for agent download
    sudo firewall-cmd --zone=public --add-port=53229/tcp --permanent
    # port for AQMP
    sudo firewall-cmd --zone=public --add-port=5672/tcp --permanent
    # port for diamond
    sudo firewall-cmd --zone=public --add-port=8101/tcp --permanent
    sudo firewall-cmd --zone=public --add-port=8100/tcp --permanent

    sudo firewall-cmd --reload

else
    echo "Skipping update firewall, please update rules manually"
fi