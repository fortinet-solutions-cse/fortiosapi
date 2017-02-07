#!/bin/bash

# Startup all celeryd
shopt -s nullglob; for f in /etc/init.d/celeryd-*; do /usr/sbin/service ${f##*/} start; done