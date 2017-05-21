#!/bin/bash

#     Click here to download the get-cloudify-composer.py script (if the download doesn't automatically begin within a few seconds).
#  Open a terminal, then, run  sudo python get-cloudify-composer.py.
#  After the installation is complete, run  sudo /opt/cloudify-composer/nodejs/bin/node /opt/cloudify-composer/blueprint-composer/package/server.js in your terminal to start the composer.
#  Now run  localhost:3000 in your browser.
#  Enter the USERNAME: composer and PASSWORD: composer to login. 

wget -c https://raw.githubusercontent.com/cloudify-cosmo/get-cloudify.py/master/get-cloudify-composer.py
sudo python get-cloudify-composer.py
mkdir logs
sudo /opt/cloudify-composer/nodejs/bin/node /opt/cloudify-composer/blueprint-composer/package/server.js
## add https://raw.githubusercontent.com/cloudify-cosmo/cloudify-openstack-plugin/2.0.1/plugin.yaml to nodes types
