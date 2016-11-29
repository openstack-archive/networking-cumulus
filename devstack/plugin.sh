#!/usr/bin/env bash
# plugin.sh - DevStack plugin.sh dispatch script template

NETWORKING_CUMULUS_DIR=${NETWORKING_CUMULUS_DIR:-$DEST/networking-cumulus}

function install_networking_cumulus {
    setup_develop $NETWORKING_CUMULUS_DIR
}


function configure_networking_cumulus {
    if [[ -z "$Q_ML2_PLUGIN_MECHANISM_DRIVERS" ]]; then
        Q_ML2_PLUGIN_MECHANISM_DRIVERS='cumulus'
    else
        if [[ ! $Q_ML2_PLUGIN_MECHANISM_DRIVERS =~ $(echo '\<cumulus\>') ]]; then
            Q_ML2_PLUGIN_MECHANISM_DRIVERS+=',cumulus'
        fi
    fi
    populate_ml2_config /$Q_PLUGIN_CONF_FILE ml2 mechanism_drivers=$Q_ML2_PLUGIN_MECHANISM_DRIVERS
}

# check for service enabled
if is_service_enabled networking_cumulus; then

    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing Networking Cumulus ML2"
        install_networking_cumulus

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Configuring Networking Cumulus Ml2"
        configure_networking_cumulus
    fi
fi
