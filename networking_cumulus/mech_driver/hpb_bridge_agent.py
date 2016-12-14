# Copyright 2016 Cumulus Networks
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

from oslo_config import cfg
from oslo_log import log as logging

from neutron.common import config as common_config
from neutron.common import utils as neutron_utils
from neutron.plugins.linuxbridge.agent import linuxbridge_neutron_agent as lna

from utils.discovery import DiscoveryManager
from utils.misc import Shell

from networking_cumulus._i18n import _, _LE, _LI

DEFAULT_ROOT_HELPER = _('sudo')

LOG = logging.getLogger(__name__)


class HPBLinuxBridgeNeutronAgentRPC(lna.LinuxBridgeNeutronAgentRPC):
    def __init__(self, interface_mappings, polling_interval):
        super(HPBLinuxBridgeNeutronAgentRPC, self).__init__(
            interface_mappings,
            polling_interval
        )

        dm = DiscoveryManager(Shell(DEFAULT_ROOT_HELPER))

        for physnet, interface in interface_mappings.iteritems():
            neighbor = dm.find_neighbor_for_interface(interface)
            if neighbor:
                self.agent_state['configurations']['switch_name'] = \
                    neighbor['name']
                self.agent_state['configurations']['switch_mgmt_ip'] = \
                    neighbor['mgmt-ip']
                break
        else:
            msg = (_("Unable to find %(nbr)s for interface %(intf)s") %
                   {'nbr': physnet,
                    'intf': interface})
            LOG.error(msg)
#                _LE('Unable to find %s neighbor for interface %s'),
#                physnet,
#                interface
#            )


def main():
    common_config.init(sys.argv[1:])

    common_config.setup_logging()
    try:
        interface_mappings = neutron_utils.parse_mappings(
            cfg.CONF.LINUX_BRIDGE.physical_interface_mappings)
    except ValueError as e:
        LOG.error(_LE("Parsing physical_interface_mappings failed: %s. "
                      "Agent terminated!"), e)
        sys.exit(1)
    LOG.info(_LI("Interface mappings: %s"), interface_mappings)

    polling_interval = cfg.CONF.AGENT.polling_interval
    agent = HPBLinuxBridgeNeutronAgentRPC(interface_mappings,
                                          polling_interval)
    LOG.info(_LI("Agent initialized successfully, now running... "))
    agent.daemon_loop()
    sys.exit(0)
