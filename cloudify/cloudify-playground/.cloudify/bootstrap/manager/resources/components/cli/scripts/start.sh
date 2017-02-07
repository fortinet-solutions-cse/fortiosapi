#!/bin/bash -e

export CFY_VIRTUALENV='~/cfy'

ctx logger info "Activating cfy virtualenv..."
. ${CFY_VIRTUALENV}/bin/activate
ctx logger info "Using localhost as Manager..."
cfy use -t localhost
