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

import neutron.db.api as db_api
import neutron.db.models.segment as seg_models

from networking_cumulus.mech_driver import models as db_models

VLAN_SEGMENTATION = 'vlan'


def db_create_network(tenant_id, network_id, vlan_id, bridge_name):
    session = db_api.get_session()
    with session.begin():
        network = (session.query(db_models.CumulusNetworks)
                   .filter_by(network_id=network_id,
                              tenant_id=tenant_id).first())

        if not network:
            network = db_models.CumulusNetworks(network_id=network_id,
                                                tenant_id=tenant_id,
                                                segmentation_id=vlan_id,
                                                bridge_name=bridge_name)
            session.add(network)


def db_delete_network(tenant_id, network_id):
    session = db_api.get_session()
    with session.begin():
        (session.query(db_models.CumulusNetworks)
         .filter_by(network_id=network_id,
                    tenant_id=tenant_id).delete())


def db_get_bridge_name(tenant_id, network_id):
    session = db_api.get_session()
    with session.begin():
        network = (session.query(db_models.CumulusNetworks)
                   .filter_by(network_id=network_id,
                              tenant_id=tenant_id).first())
        if network:
            return network.bridge_name
        else:
            return None


def db_get_network(tenant_id, network_id):
    session = db_api.get_session()
    with session.begin():
        network = (session.query(db_models.CumulusNetworks)
                   .filter_by(network_id=network_id,
                              tenant_id=tenant_id).first())
        if network:
            return network
        else:
            return None


def db_get_seg_type(network_id):
    session = db_api.get_session()
    with session.begin():
        segment = (session.query(seg_models.NetworkSegment)
                   .filter_by(network_id=network_id).first())
        if segment:
            return segment.network_type
        else:
            return None


def db_create_port(tenant_id, network_id, port_id, host_id, device_id,
                   bridge_name, server_id, vni):
    session = db_api.get_session()
    with session.begin():
        port = (session.query(db_models.CumulusPorts)
                .filter_by(network_id=network_id,
                           tenant_id=tenant_id,
                           server_id=server_id,
                           host_id=host_id).first())

        if not port:
            port = db_models.CumulusPorts(port_id=port_id,
                                          tenant_id=tenant_id,
                                          network_id=network_id,
                                          host_id=host_id,
                                          device_id=device_id,
                                          bridge_name=bridge_name,
                                          server_id=server_id,
                                          vni=vni)
            session.add(port)


def db_delete_port(network_id, port_id, server_id, host_id):
    session = db_api.get_session()
    with session.begin():
        session.query(db_models.CumulusPorts).filter_by(
            network_id=network_id,
            port_id=port_id,
            server_id=server_id,
            host_id=host_id).delete()


def db_update_port(tenant_id, network_id, port_id, host_id, device_id,
                   bridge_name, server_id, vni):
    session = db_api.get_session()
    with session.begin():
        all_ports = (session.query(db_models.CumulusPorts)
                     .filter_by(network_id=network_id,
                                port_id=port_id,
                                server_id=server_id).all())
        for port in all_ports:
            port.host_id = host_id
            port.device_id = device_id
            port.vni = vni


def db_get_ports_by_server_id(server_id):
    session = db_api.get_session()
    with session.begin():
        all_ports = (session.query(db_models.CumulusPorts)
                     .filter_by(server_id=server_id).all())
        return all_ports


def db_get_port(network_id, port_id, server_id, host_id):
    session = db_api.get_session()
    with session.begin():
        port = session.query(db_models.CumulusPorts).filter_by(
            network_id=network_id,
            port_id=port_id,
            server_id=server_id,
            host_id=host_id).first()

        if port:
            return port
        else:
            return None
