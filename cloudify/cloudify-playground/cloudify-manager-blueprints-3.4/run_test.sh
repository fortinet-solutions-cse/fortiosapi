#!/bin/bash -e

if [ $1 == "validate-blueprints" ]; then
  cfy init
  blueprints=`find . -name "*-manager-blueprint.yaml"`
  for blueprint in $blueprints; do
    cfy blueprints validate -p $blueprint
  done
elif [ $1 == "flake8" ]; then
  flake8 .
elif [ $1 == "bootstrap-sanity" ]; then
  #TAG=$(git describe --exact-match --tags HEAD)
  #if [ "${TAG}" == "bootstrap-sanity" ]; then
  if [ "${TAG}" == "bootstrap-sanity" ] || [ "${CIRCLE_TAG}" == "bootstrap-sanity" ]; then
    cd tests
    pip install -r bootstrap-sanity-requirements.txt
    python sanity.py
    exit $?
  else
    echo "Not bootstrap-sanity tag, skipping bootstrap sanity test."
  fi;
else
  exit 1
fi;

