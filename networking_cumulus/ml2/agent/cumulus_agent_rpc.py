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
import oslo_messaging

from networking_cumulus._i18n import _LI
from networking_cumulus.common import constants as c_const

from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron.extensions import providernet as pnet

from networking_cumulus.netconf import netconf

LOG = log.getLogger(__name__)


class CumulusAgentRpcCallbacks(object):

    target = oslo_messaging.Target(version='1.2')

    def create_network(self, context, current):
        segmentation_id = current[pnet.SEGMENTATION_ID]
        LOG.debug("Creating network with vlan %(segmentation_id)d ",
                  {'segmentation_id': segmentation_id})
        with netconf.ConfFile(netconf.INT_BRIDGE) as cfg:
            cfg.ensure_opt_contain_value('bridge-vids', str(segmentation_id))
        LOG.info(_LI("Network with vlan %(segmentation_id)d was created."),
                 {'segmentation_id': segmentation_id})

    def delete_network(self, context, current):
        segmentation_id = current[pnet.SEGMENTATION_ID]
        with netconf.ConfFile(netconf.INT_BRIDGE) as cfg:
            cfg.ensure_opt_not_contain_value('bridge-vids',
                                             str(segmentation_id))
        LOG.debug("Network with vlan %(segmentation_id)d was deleted.",
                  {'segmentation_id': segmentation_id})

    def plug_port_to_network(self, context, port_id, segmentation_id):
        with netconf.ConfFile(netconf.INT_BRIDGE) as cfg:
            cfg.ensure_opt_contain_value('bridge-ports', port_id)

        with netconf.ConfFile(port_id) as int_cfg:
            int_cfg.ensure_opt_has_value('bridge-access', str(segmentation_id))
        LOG.info(_LI("Port %(port_id)s was plugged to vlan "
                     "%(segmentation_id)d "),
                 {'segmentation_id': segmentation_id,
                  'port_id': port_id})

    def delete_port_from_network(self, context, port_id, segmentation_id):
        with netconf.ConfFile(netconf.INT_BRIDGE) as cfg:
            cfg.ensure_opt_not_contain_value('bridge-ports', port_id)

        with netconf.ConfFile(port_id) as int_cfg:
            int_cfg.ensure_opt_not_contain_value('bridge-access',
                                                 str(segmentation_id))
        LOG.info(_LI("Port %(port_id)s was removed from vlan "
                     "%(segmentation_id)d "),
                 {'segmentation_id': segmentation_id,
                  'port_id': port_id})


class CumulusRpcClientAPI(object):

    """Agent side of the Cumulusrpc API."""
    ver = '1.2'

    def __init__(self, context):
        target = oslo_messaging.Target(topic=c_const.CUMULUS, version=self.ver)
        self.client = n_rpc.get_client(target)
        self.context = context

    def _get_device_topic(self, host=None):
        return topics.get_topic_name(topics.AGENT,
                                     c_const.CUMULUS,
                                     topics.UPDATE, host)

    def _get_cctxt(self, host=None):
        return self.client.prepare(
            version=self.ver, topic=self._get_device_topic(host=host))

    def create_network_cast(self, current, host=None):
        return self._get_cctxt(host).cast(self.context, 'create_network',
                                          current=current)

    def delete_network_cast(self, current, host=None):
        return self._get_cctxt(host).cast(self.context, 'delete_network',
                                          current=current)

    def plug_port_to_network(self, host, port_id, segmentation_id):
        return self._get_cctxt(host).call(
            self.context, 'plug_port_to_network', port_id=port_id,
            segmentation_id=segmentation_id)

    def delete_port(self, host, port_id, segmentation_id):
        return self._get_cctxt(host).call(
            self.context, 'delete_port_from_network', port_id=port_id,
            segmentation_id=segmentation_id)
