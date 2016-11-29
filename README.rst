#####################################
networking-cumulus Neutron ML2 driver
#####################################

This is a Cumulus Modular Layer 2 `Neutron Mechanism driver
<https://wiki.openstack.org/wiki/Neutron/ML2>`_ that provides
Neutron and CumulusLinux integraion.

* Code: http://git.openstack.org/cgit/openstack/networking-cumulus
* Bugs: https://bugs.launchpad.net/networking-cumulus
* Docs: TBD


Architecture
------------

 :: TODO

Deploying networking-cumulus with DevStack
------------------------------------------

DevStack may be configured to deploy networking-cumulus, setup Neutron to
use the networking-cumulus ML2 driver. It is highly recommended
to deploy on an expendable virtual machine and not on your personal work
station.  Deploying networking-cumulus with DevStack requires a machine
running Ubuntu 14.04 (or later) or Fedora 20 (or later).

.. seealso::

    http://docs.openstack.org/developer/devstack/

Devstack will no longer create the user 'stack' with the desired
permissions, but does provide a script to perform the task::

    git clone https://github.com/openstack-dev/devstack.git devstack
    sudo ./devstack/tools/create-stack-user.sh

Switch to the stack user and clone DevStack::

    sudo su - stack
    git clone https://github.com/openstack-dev/devstack.git devstack

Add the following to devstack/local.conf to enable networking-cumulus::

    enable_plugin networking-cumulus https://git.openstack.org/openstack/networking-cumulus


Setup neutron-cumulus-agent on Cumulus VX
-----------------------------------------

Detailed instructions how to set Cumulus VX may be found `here
<https://docs.cumulusnetworks.com/display/VX/Cumulus+VX+Getting+Started+Guide>`_

#. Install git on `CumulusLinux`::

    apt-get update
    apt-get install build-essential python-dev git
    easy_install pip

#. Install python-neutron::

    pip install git+http://github.com/openstack/neutron

#. Download networking-cumulus on CumulusLinux host::

    git clone https://github.com/openstack/networking-cumulus
    cd networking-cumulus/

#. Install neutron-cumulus-agent::

    pip install -e ./

    # Copy configs
    mkdir /etc/neutron-cumulus
    cp etc/neutron-cumulus/* /etc/neutron-cumulus/ -R

#. Setup minimal `/etc/neutron-cumulus/neutron-cumulus.conf`::

    [DEFAULT]
    host=cumulus
    debug = True
    transport_url = rabbit://${RABBIT_USERID}:${RABBIT_PASSWORD}@${DEVSTACK_HOST_IP}:5672/
    bind_host = 0.0.0.0

#. Start `neutron-cumulus-agent`::

    neutron-cumulus-agent --config-file /etc/neutron-cumulus/neutron-cumulus.conf

#. Verify that `Cumulus Agent` has been registered in Neutron::

    neutron agent-list
