# -*- mode: shell-script -*-

function install_lldp() {
    echo_summary "Installing LLDP"
    install_package lldpd
    start_service lldpd
}

function install_cumulus_driver() {
    echo_summary "Installing Cumulus Mechanism Driver"
    setup_develop $CUMULUS_DIR
}

function configure_cumulus_driver() {
    echo_summary "Configuring Neutron for Cumulus Driver"
    cp $CUMULUS_ML2_CONF_SAMPLE $CUMULUS_ML2_CONF_FILE
}

if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
    if is_service_enabled "q-agt"; then
        install_lldp
    fi

elif [[ "$1" == "stack" && "$2" == "install" ]]; then
    install_cumulus_driver

elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    configure_cumulus_driver

elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
    # no-op
    :
fi

if [[ "$1" == "unstack" ]]; then
    # no-op
    :
fi

if [[ "$1" == "clean" ]]; then
    # no-op
    :
fi
