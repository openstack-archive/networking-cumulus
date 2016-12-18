=====================================
networking-cumulus Neutron ML2 driver
=====================================

Cumulus ML2 Mechanism Driver for Neutron

* Free software: Apache license
* Documentation: TBD
* Source: http://git.openstack.org/cgit/openstack/networking-cumulus
* Bugs: http://bugs.launchpad.net/networking-cumulus

Configuration
=============

List of switches are required to be configured in
``/etc/neutron/plugins/ml2/ml2_conf_cumulus.ini``. 
The list can be comma separated switch names or IPs.
All other configurable parameters are optional.

Cumulus ML2 driver confiuration format:

    [ml2_cumulus]
    switches = <list of IP addresses or names>
    protocol_port = <rest api port>
    sync_time = <time interval in secs>
    spf_time = <True/False>
    new_bridge = <True/False>

Example of ``ml2_conf_cumulus.ini``:

    [ml2_cumulus]
    switches = 192.168.10.10,192.168.20.20
    sync_time = 10
    new_bridge = False
    spf_enable = False


The ``cumulus`` mechanism driver needs to be enabled from
the ml2 config file ``/etc/neutron/plugins/ml2/ml2_conf.ini``::

   [ml2]
   tenant_network_types = vlan
   type_drivers = vlan,vxlan
   mechanism_drivers = linuxbridge,cumulus
   ...
   ...

(Re)start ``neutron-server`` specifying cumulus additional configuration file::

    neutron-server \
        --config-file /etc/neutron/neutron.conf \
        --config-file /etc/neutron/plugins/ml2/ml2_conf.ini \
        --config-file /etc/neutron/plugins/ml2/ml2_conf_cumulus.ini
