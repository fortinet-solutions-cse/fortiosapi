#!/bin/bash -x

lxc launch ubuntu:16.04 riftio-launchpad

#Follow https://open.riftio.com/documentation/riftware/4.3/a/install/install-riftware-on-generic-system.htm
#Run curl or wget to download the install-launchpad script. For example:

sleep 24

LXC="lxc exec riftio-launchpad"
$LXC ping -c 4 riftio.com
$LXC wget http://repo.riftio.com/releases/open.riftio.com/4.3.3/install-launchpad
#Run the install-launchpad script.
$LXC apt -y install libxml2-dev libxslt-dev
$LXC bash install-launchpad

lxc restart riftio-launchpad
