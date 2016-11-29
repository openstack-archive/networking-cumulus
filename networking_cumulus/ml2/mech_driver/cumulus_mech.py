#
# Copyright (c) 2016 Mirantis Inc.
#
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

from oslo_log import log

from neutron import context as neutron_context
from neutron.extensions import portbindings
from neutron.plugins.common import constants as p_const
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2.drivers import mech_agent

from networking_cumulus._i18n import _LI
from networking_cumulus.common import constants
from networking_cumulus.ml2.agent import cumulus_agent_rpc

LOG = log.getLogger(__name__)


class CumulusLBAgentMechanismDriver(mech_agent.SimpleAgentMechanismDriverBase):
    """Attach to networks using linux bridges on Cumulus switch.

    The CumulusLBAgentMechanismDriver integrates the ml2 plugin with the
    Cumulus Agent. Port binding with this driver requires the
    Cumulus Agent to be running on the cumulus switch.
    """
    def __init__(self):
        super(CumulusLBAgentMechanismDriver, self).__init__(
            constants.AGENT_TYPE_CUMULUS,
            portbindings.VIF_TYPE_OTHER,
            {portbindings.CAP_PORT_FILTER: True})
        self.context = neutron_context.get_admin_context()
        self._start_rpc_listeners()
        self._pool = None
        self.supported_vnic_types = [portbindings.VNIC_BAREMETAL]
        self.supported_network_types = [p_const.TYPE_VLAN]
        LOG.info(_LI("Successfully initialized Cumulus Mechanism driver."))

    def get_allowed_network_types(self, agent):
        return (agent['configurations'].get('tunnel_types', []) +
                [p_const.TYPE_VLAN])

    def get_mappings(self, agent):
        return agent['configurations'].get('bridge_mappings', {})

    def _start_rpc_listeners(self):
        self.agent_notifier = cumulus_agent_rpc.CumulusRpcClientAPI(
            self.context)

    def create_port_postcommit(self, context):
        pass

    def update_port_postcommit(self, context):
        pass

    def delete_port_postcommit(self, context):
        """Delete port non-database commit event."""
        port = context.current
        if port and port[portbindings.VNIC_TYPE] in self.supported_vnic_types:
            segment = context.top_bound_segment
            binding_profile = port[portbindings.PROFILE]
            local_link_inf = binding_profile.get('local_link_information')
            segmentation_id = segment.get('segmentation_id')
            if (segment and
                (segment[api.NETWORK_TYPE] in
                 self.supported_network_types) and
                    local_link_inf):
                for lli in local_link_inf:
                    switch_name = lli.get('switch_info')
                    port_id = lli.get('port_id')
                    LOG.debug("Removing port $(port_id)s on switch "
                              "%(switch_name)s from "
                              "vlan %(segmentation_id)s",
                              {'port_id': port_id,
                               'switch_name': switch_name,
                               'segmentation_id': segmentation_id})
                    self.agent_notifier.delete_port(
                        host=switch_name, port_id=port_id,
                        segmentation_id=segmentation_id)

    def create_network_postcommit(self, context):
        self.agent_notifier.create_network_cast(current=context.current)

    def delete_network_postcommit(self, context):
        self.agent_notifier.delete_network_cast(current=context.current)

    def bind_port(self, context):
        segments = context.network.network_segments
        for segment in segments:
            if segment[api.NETWORK_TYPE] in self.supported_network_types:
                port = context.current
                binding_profile = port[portbindings.PROFILE]
                local_link_inf = binding_profile.get('local_link_information')
                vnic_type = port[portbindings.VNIC_TYPE]
                if vnic_type in self.supported_vnic_types and local_link_inf:
                    for lli in local_link_inf:
                        switch_name = lli.get('switch_info')
                        port_id = lli.get('port_id')
                        segmentation_id = segment.get('segmentation_id')
                        LOG.debug("Adding port %(port_id)s on switch "
                                  "%(switch_name)s to vlan "
                                  " %(segmentation_id)s",
                                  {'port_id': port_id,
                                   'switch_name': switch_name,
                                   'segmentation_id': segmentation_id})
                        self.agent_notifier.plug_port_to_network(
                            host=switch_name, port_id=port_id,
                            segmentation_id=segmentation_id)
                        context.set_binding(segment[api.ID],
                                            portbindings.VIF_TYPE_OTHER, {})
