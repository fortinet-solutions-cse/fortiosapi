#!/bin/bash -x


lxc delete cfy-mngr  --force
rm -rf cfy_virtualenv
rm -rf cloudify-manager-blueprints
