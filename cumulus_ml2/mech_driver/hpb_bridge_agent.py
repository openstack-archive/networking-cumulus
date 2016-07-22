import sys

from oslo_config import cfg
from oslo_log import log as logging

from neutron.common import config as common_config
from neutron.common import utils as neutron_utils
from neutron.i18n import _LE, _LI, _LW
from neutron.plugins.linuxbridge.agent import linuxbridge_neutron_agent as lna

from utils.discovery import DiscoveryManager
from utils.misc import Shell

DEFAULT_ROOT_HELPER = 'sudo'

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
            LOG.error(
                _LE('Unable to find %s neighbor for interface %s'),
                physnet,
                interface
            )


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

