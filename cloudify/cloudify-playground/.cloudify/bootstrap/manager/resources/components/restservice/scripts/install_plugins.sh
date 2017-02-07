#!/bin/bash -e

VENV=/opt/manager/env

echo "Installing rest service plugins"
. $VENV/bin/activate

{% for name, plugin in plugins.iteritems() %}

    echo "Installing {{ name }} plugin in rest service virtual environment"

    extract_plugin_script="import sys;\
    from cloudify_agent.api.plugins.installer import extract_package_to_dir;\
    sys.stdout.write(extract_package_to_dir('{{ plugin.source }}'));\
    "

    plugin_dir=$(python -c "${extract_plugin_script}")

    pushd ${plugin_dir}
        if [[ {{ plugin.source }} == *.wgn ]]; then
            # install wagon plugin
            sudo $VENV/bin/pip install {{ plugin.install_args }}
        else
            sudo $VENV/bin/pip install . {{ plugin.install_args }}
        fi
    popd

    echo "{{ name }} was successfully installed"

{% endfor %}