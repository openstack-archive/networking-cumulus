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

import sqlalchemy as sa

from neutron_lib.db import constants
from neutron_lib.db import model_base

BRIDGE_STR_LEN = 15
CUMULUS_UUID_FIELD_SIZE = 36


class CumulusNetworks(model_base.BASEV2, model_base.HasId):
    """Represents a binding of network id to cumulus bridge."""

    __tablename__ = "cumulus_networks"

    network_id = sa.Column(sa.String(CUMULUS_UUID_FIELD_SIZE))
    segmentation_id = sa.Column(sa.Integer)
    bridge_name = sa.Column(sa.String(BRIDGE_STR_LEN))
    tenant_id = sa.Column(sa.String(constants.NAME_FIELD_SIZE))

    def __init__(self, network_id=None, tenant_id=None, segmentation_id=None,
                 bridge_name=None, **kwargs):
        super(CumulusNetworks, self).__init__(**kwargs)
#        self.id = network_id
        self.network_id = network_id
        self.tenant_id = tenant_id
        self.bridge_name = bridge_name
        self.segmentation_id = segmentation_id

    def network_representation(self):
        return {u'networkId': self.network_id,
                u'tenantId': self.tenant_id,
                u'segmentationId': self.segmentation_id,
                u'bridgeName': self.bridge_name}


class CumulusPorts(model_base.BASEV2, model_base.HasId):

    __tablename__ = "cumulus_ports"

    network_id = sa.Column(sa.String(CUMULUS_UUID_FIELD_SIZE))
    port_id = sa.Column(sa.String(CUMULUS_UUID_FIELD_SIZE))
    device_id = sa.Column(sa.String(constants.NAME_FIELD_SIZE))
    bridge_name = sa.Column(sa.String(BRIDGE_STR_LEN))
    server_id = sa.Column(sa.String(constants.NAME_FIELD_SIZE))
    host_id = sa.Column(sa.String(constants.NAME_FIELD_SIZE))
    vni = sa.Column(sa.Integer)
    tenant_id = sa.Column(sa.String(constants.NAME_FIELD_SIZE))

    def __init__(self, port_id=None, tenant_id=None, network_id=None,
                 device_id=None, server_id=None, bridge_name=None,
                 host_id=None, vni=None, **kwargs):
        super(CumulusPorts, self).__init__(**kwargs)
        self.port_id = port_id
        self.tenant_id = tenant_id
        self.network_id = network_id
        self.device_id = device_id
        self.server_id = server_id
        self.bridge_name = bridge_name
        self.host_id = host_id
        self.vni = vni

    def port_representation(self):
        return {u'networkId': self.network_id,
                u'tenantId': self.tenant_id,
                u'portId': self.port_id,
                u'deviceId': self.device_id,
                u'bridgeName': self.bridge_name,
                u'host': self.host_id,
                u'serverId': self.server_id,
                u'vni': self.vni}
