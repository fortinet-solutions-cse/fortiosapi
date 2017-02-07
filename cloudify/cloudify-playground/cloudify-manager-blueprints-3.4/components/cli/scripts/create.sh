#!/bin/bash -e

. $(ctx download-resource "components/utils")

export REST_CLIENT_SOURCE_URL=$(ctx node properties rest_client_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-rest-client/archive/3.2.zip")
export DSL_PARSER_SOURCE_URL=$(ctx node properties dsl_parser_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-manager/archive/3.2.tar.gz")
export PLUGINS_COMMON_SOURCE_URL=$(ctx node properties plugins_common_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-plugins-common/archive/3.2.zip")
export SCRIPT_PLUGIN_SOURCE_URL=$(ctx node properties script_plugin_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-script-plugin/archive/1.2.zip")
export CLI_SOURCE_URL=$(ctx node properties cli_module_source_url)

export CFY_VIRTUALENV='~/cfy'

ctx logger info "Creating virtualenv ${CFY_VIRTUALENV}..."
create_virtualenv "${CFY_VIRTUALENV}"

ctx logger info "Installing Prerequisites..."
# instead of installing these, our build process should create wheels of the required dependencies which could be later installed directory
# sudo yum install -y python-devel g++ gcc # libxslt-dev libxml2-dev
yum_install "python-devel g++ gcc" >/dev/null

ctx logger info "Installing CLI Modules..."
install_module ${REST_CLIENT_SOURCE_URL} ${CFY_VIRTUALENV}
install_module ${DSL_PARSER_SOURCE_URL} ${CFY_VIRTUALENV}
install_module ${PLUGINS_COMMON_SOURCE_URL} ${CFY_VIRTUALENV}
install_module ${SCRIPT_PLUGIN_SOURCE_URL} ${CFY_VIRTUALENV}
install_module ${CLI_SOURCE_URL} ${CFY_VIRTUALENV}