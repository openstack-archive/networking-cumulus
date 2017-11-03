# Copyright 2016,2017 Cumulus Networks
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

import json

import threading

from enum import Enum

from oslo_config import cfg
from oslo_log import log as logging
import requests

from neutron.extensions import portbindings
from neutron.plugins.ml2.common.exceptions import MechanismDriverError
from neutron.plugins.ml2 import driver_api as api

from neutron_lib.api.definitions import provider_net as pnet
from neutron_lib import constants as const

from networking_cumulus._i18n import _, _LI
from networking_cumulus.mech_driver import config  # noqa
from networking_cumulus.mech_driver import db

LOG = logging.getLogger(__name__)
NETWORKS_URL = _('{scheme}://{base}:{port}/ml2/v1/bridge/{bridge}/{vlanid}')
HOSTS_URL = \
    _('{scheme}://{base}:{port}/ml2/v1/bridge/{bridge}/{vlanid}/hosts/{host}')
VXLAN_URL = \
    _('{scheme}://{base}:{port}/ml2/v1/bridge/{bridge}/{vlanid}/vxlan/{vni}')
SWITCH_HASH_ID_URL = _('{scheme}://{base}:{port}/ml2/v1/hash')

NEW_BRIDGE_NAME = _('bridge')

OLD_BRIDGE_NAME_PREFIX = _('br')


class SwitchState(Enum):
    inactive = 1
    active = 2

INVALID_HASH_ID = _('invalid')
INVALID_VNI = -1
INVALID_VLAN_ID = -1


class CumulusMechanismDriver(api.MechanismDriver):
    """Mechanism driver for Cumulus Linux

    It manages connectivity between switches and (compute) hosts
    using the Cumulus API
    """
    def __init__(self):
        self.scheme = cfg.CONF.ml2_cumulus.scheme
        self.protocol_port = cfg.CONF.ml2_cumulus.protocol_port
        self.switches = cfg.CONF.ml2_cumulus.switches
        self.sync_timeout = cfg.CONF.ml2_cumulus.sync_time
        self.spf_enable = cfg.CONF.ml2_cumulus.spf_enable
        self.new_bridge = cfg.CONF.ml2_cumulus.new_bridge
        self.username = cfg.CONF.ml2_cumulus.username
        self.password = cfg.CONF.ml2_cumulus.password
        self.switch_info = {}
        self.sync_timer = None
        self.sync_thread_lock = threading.Lock()
        self.sync = None

    def initialize(self):

        for switch_id in self.switches:
            self.switch_info[switch_id, 'spf_enable'] = self.spf_enable
            self.switch_info[switch_id, 'new_bridge'] = self.new_bridge

        if self.sync_timeout > 0:
            self.sync = CumulusSwitchSync(self)
            self.sync_timer = None
            self._start_sync_thread()

    def _start_sync_thread(self):
        with self.sync_thread_lock:
            self.sync.check_and_replay()

        self.sync_timer = threading.Timer(self.sync_timeout,
                                          self._start_sync_thread)
        self.sync_timer.start()

    def stop_sync_thread(self):
        if self.sync_timer:
            self.sync_timer.cancel()
            self.sync_time = None

    def get_bridge_name(self, network_id, new_bridge):
        if new_bridge:
            return NEW_BRIDGE_NAME
        else:
            bridge_name = OLD_BRIDGE_NAME_PREFIX + network_id[:12]
            return bridge_name

    def _get_segment_ids(self, top_segment, bottom_segment):
        if top_segment is None:
            return INVALID_VLAN_ID, INVALID_VNI, False
        elif top_segment[api.NETWORK_TYPE] == const.TYPE_VXLAN:
            return bottom_segment[api.SEGMENTATION_ID],\
                top_segment[api.SEGMENTATION_ID], True
        else:
            return top_segment[api.SEGMENTATION_ID], INVALID_VNI, False

    def bind_port(self, context):

        port = context.current
        if context.binding_levels:
            return  # we've already got a top binding
        for segment in context.segments_to_bind:
            physnet = segment.get(api.PHYSICAL_NETWORK)
            # If physnet was not found, we cannot bind this port
            if not physnet:
                LOG.debug("bind_port for port %(port)s: no physical_network "
                          "found", {'port': port.get('id')})
                continue

            if segment[api.NETWORK_TYPE] == const.TYPE_VXLAN:

                try:
                    next_segment = context.allocate_dynamic_segment(
                        {'id': context.network.current['id'],
                         'network_type': 'vlan',
                         'physical_network': physnet})
                except Exception as exc:
                    LOG.error(_LI("cumulus bind_port for port %(port)s: Failed"
                                  " to allocate dynamic segment for physnet "
                                  "%(physnet)s. %(exc)s"),
                              {'port': port.get('id'), 'physnet': physnet,
                               'exc': exc})
                    return

                context.continue_binding(
                    segment['id'],
                    [next_segment]
                )

    def create_network_precommit(self, context):
        network = context.current
        network_id = network['id']
        tenant_id = network['tenant_id']

        if (network[pnet.NETWORK_TYPE] != const.TYPE_VLAN) and\
           (network[pnet.NETWORK_TYPE] != const.TYPE_VXLAN):
            return

        if network[pnet.SEGMENTATION_ID]:
            seg_id = network[pnet.SEGMENTATION_ID]
        else:
            return

        with self.sync_thread_lock:
            db.db_create_network(tenant_id,
                                 network_id,
                                 seg_id,
                                 self.get_bridge_name(network_id,
                                                      self.new_bridge))

    def create_network_postcommit(self, context):

        # Returning from here, since the create_port_postcommit or
        # update_port_postcommit takes care of provision network on the
        # hardware.

        return

    def delete_network_postcommit(self, context):
        network_id = context.current['id']
        tenant_id = context.current['tenant_id']

        with self.sync_thread_lock:
            db.db_delete_network(tenant_id, network_id)

    def create_port_precommit(self, context):
        if not hasattr(context, 'current'):
            return

        port = context.current
        port_id = port['id']
        device_id = port['device_id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        host = port[portbindings.HOST_ID]

        vlan_id, vni, is_vxlan = (self._get_segment_ids(
                                  context.top_bound_segment,
                                  context.bottom_bound_segment))

        with self.sync_thread_lock:
            bridge_name = db.db_get_bridge_name(tenant_id, network_id)
            if not bridge_name:
                return

            for _switch_id in self.switches:
                db.db_create_port(tenant_id, network_id, port_id, host,
                                  device_id, bridge_name, _switch_id, vlan_id)

    def create_port_postcommit(self, context):
        if not hasattr(context, 'current'):
            return

        port = context.current
        network_id = port['network_id']
        tenant_id = port['tenant_id']

        with self.sync_thread_lock:
            network = db.db_get_network(tenant_id, network_id)
            if not network:
                return

        if context.segments_to_bind:
            self._add_to_switch(context, network)

    def update_port_postcommit(self, context):
        if not hasattr(context, 'current'):
            return

        port = context.current
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        device_id = port['device_id']
        host = port[portbindings.HOST_ID]
        orig_port = context.original
        orig_host = orig_port[portbindings.HOST_ID]
        orig_vlan_id = None

        if not host:
            return

        vlan_id, vni, is_vxlan = (self._get_segment_ids(
                                  context.top_bound_segment,
                                  context.bottom_bound_segment))
        if vlan_id == INVALID_VLAN_ID:
            return

        with self.sync_thread_lock:
            network = db.db_get_network(tenant_id, network_id)
            if not network:
                return
            for _switch_id in self.switches:
                db_port = db.db_get_port(network_id, port_id, _switch_id, host)
                if db_port:
                    orig_vlan_id = db_port.vni
                    break

        if (orig_host != host) or (orig_vlan_id != vlan_id):
            if orig_vlan_id != INVALID_VLAN_ID:
                self._remove_from_switch(context.original, network, True)
            self._add_to_switch(context, network)

        with self.sync_thread_lock:
            for _switch_id in self.switches:
                db_port = db.db_get_port(network_id, port_id, _switch_id, host)
                if not db_port:
                    db.db_create_port(tenant_id, network_id, port_id,
                                      host, device_id,
                                      network.bridge_name, _switch_id, vlan_id)
                else:
                    db.db_update_port(tenant_id, network_id, port_id,
                                      host, device_id,
                                      network.bridge_name, _switch_id, vlan_id)

    def delete_port_postcommit(self, context):
        if not hasattr(context, 'current'):
            return

        port = context.current
        network_id = port['network_id']
        tenant_id = port['tenant_id']

        with self.sync_thread_lock:
            network = db.db_get_network(tenant_id, network_id)
            if not network:
                return

        self._remove_from_switch(port, network, True)

    def _add_to_switch(self, context, network):

        port = context.current
        device_id = port['device_id']
        device_owner = port['device_owner']
        host = port[portbindings.HOST_ID]
        if not hasattr(context, 'top_bound_segment') or \
           (context.top_bound_segment is None):
            return

        if not (host and device_id and device_owner):
            return

        vlan_id, vni, is_vxlan = (self._get_segment_ids(
                                  context.top_bound_segment,
                                  context.bottom_bound_segment))

        if vlan_id == INVALID_VLAN_ID:
            return

        for _switch_id in self.switches:
            try:
                resp = requests.put(
                    NETWORKS_URL.format(
                        scheme=self.scheme,
                        base=_switch_id,
                        port=self.protocol_port,
                        bridge=network.bridge_name,
                        vlanid=vlan_id
                    ),
                    data=json.dumps(
                        {'spf':
                         self.switch_info[_switch_id, 'spf_enable'],
                         'newbridge':
                         self.switch_info[_switch_id, 'new_bridge']}),
                    auth=(self.username, self.password),
                    verify=False
                )

                if resp.status_code != requests.codes.ok:
                    raise MechanismDriverError()

            except requests.exceptions.RequestException as error:
                msg = (_("Error connecting to switch (%(switch_id)s)."
                         " HTTP Error %(error)s") %
                       {'switch_id': _switch_id,
                        'error': error})
                LOG.info(msg)
                continue

            actions = [
                HOSTS_URL.format(
                    scheme=self.scheme,
                    base=_switch_id,
                    port=self.protocol_port,
                    bridge=network.bridge_name,
                    vlanid=vlan_id,
                    host=host
                ),
            ]

            if is_vxlan:

                actions.append(
                    VXLAN_URL.format(
                        scheme=self.scheme,
                        base=_switch_id,
                        port=self.protocol_port,
                        bridge=network.bridge_name,
                        vlanid=vlan_id,
                        vni=vni
                    )
                )

            for action in actions:
                try:
                    resp = requests.put(action,
                                        auth=(self.username, self.password),
                                        verify=False)

                    if resp.status_code != requests.codes.ok:
                        msg = (_("Error (%(code)s) update port for %(host)s on"
                                 " switch %(switch_id)s") %
                               {'code': resp.status_code,
                                'host': host,
                                'switch_id': _switch_id})

                        LOG.info(msg)
                        return resp.status_code
#                    raise MechanismDriverError()

                except requests.exceptions.RequestException as error:
                    msg = (_("Error connecting to switch (%(switch_id)s)."
                             " HTTP Error %(error)s") %
                           {'switch_id': _switch_id,
                            'error': error})
                    LOG.info(msg)

    def _remove_from_switch(self, port, network, remove_net):
        host = port[portbindings.HOST_ID]
        port_id = port['id']

        with self.sync_thread_lock:
            is_vxlan = (db.db_get_seg_type(network.network_id)
                        == const.TYPE_VXLAN)

        for _switch_id in self.switches:
            with self.sync_thread_lock:
                db_port = db.db_get_port(network.network_id,
                                         port_id,
                                         _switch_id,
                                         host)
                if not db_port:
                    continue
                vlan_id = db_port.vni

            actions = [
                HOSTS_URL.format(
                    scheme=self.scheme,
                    base=_switch_id,
                    port=self.protocol_port,
                    bridge=network.bridge_name,
                    vlanid=network.segmentation_id,
                    host=host
                ),
            ]

            if (is_vxlan):
                actions.append(
                    VXLAN_URL.format(
                        scheme=self.scheme,
                        base=_switch_id,
                        port=self.protocol_port,
                        bridge=network.bridge_name,
                        vlanid=vlan_id,
                        vni=network.segmentation_id
                    )
                )

            for action in actions:
                try:
                    resp = requests.delete(action,
                                           auth=(self.username, self.password),
                                           verify=False)

                    if resp.status_code != requests.codes.ok:
                        msg = (_("Error (%(code)s) delete port for %(host)s on"
                                 " switch %(switch_id)s") %
                               {'code': resp.status_code,
                                'host': host,
                                'switch_id': _switch_id})
                        LOG.info(msg)

                except requests.exceptions.RequestException as error:
                    msg = (_("Error connecting to switch (%(switch_id)s)."
                             " HTTP Error %(error)s") %
                           {'switch_id': _switch_id,
                            'error': error})
                    LOG.info(msg)

            with self.sync_thread_lock:
                db.db_delete_port(network.network_id, port_id, _switch_id,
                                  host)
            if remove_net:
                try:
                    resp = requests.delete(
                        NETWORKS_URL.format(
                            scheme=self.scheme,
                            base=_switch_id,
                            port=self.protocol_port,
                            bridge=network.bridge_name,
                            vlanid=vlan_id
                        ),
                        auth=(self.username, self.password),
                        verify=False
                    )

                    if resp.status_code != requests.codes.ok:
                        LOG.info(
                            _LI('Error during network delete. HTTP Error:%d'),
                            resp.status_code
                        )

                except requests.exceptions.RequestException as error:
                    msg = (_("Error connecting to switch (%(switch_id)s)."
                             " HTTP Error %(error)s") %
                           {'switch_id': _switch_id,
                            'error': error})
                    LOG.info(msg)

    def replay_to_switch(self, switch_id, bridge_name, port, seg_id):

        is_vxlan = (db.db_get_seg_type(port.network_id) == const.TYPE_VXLAN)
        try:
            resp = requests.put(
                NETWORKS_URL.format(
                    scheme=self.scheme,
                    base=switch_id,
                    port=self.protocol_port,
                    bridge=bridge_name,
                    vlanid=port.vni
                ),
                data=json.dumps({'spf':
                                 self.switch_info[switch_id, 'spf_enable'],
                                 'newbridge':
                                 self.switch_info[switch_id, 'new_bridge']}),
                auth=(self.username, self.password),
                verify=False
            )

            if resp.status_code != requests.codes.ok:
                msg = (_("Error %(code)d replay to switch %(switch_id)s.") %
                       {'code': resp.status_code,
                        'switch_id': switch_id})
                LOG.info(msg)
                return resp.status_code

        except requests.exceptions.RequestException as error:
            msg = (_("Error connecting to switch %(switch_id)s."
                     " HTTP Error %(error)s") %
                   {'switch_id': switch_id,
                    'error': error})
            LOG.info(msg)

        actions = [
            HOSTS_URL.format(
                scheme=self.scheme,
                base=switch_id,
                port=self.protocol_port,
                bridge=bridge_name,
                vlanid=port.vni,
                host=port.host_id
            ),
        ]

        if is_vxlan and (seg_id != INVALID_VNI):
            actions.append(
                VXLAN_URL.format(
                    scheme=self.scheme,
                    base=switch_id,
                    port=self.protocol_port,
                    bridge=bridge_name,
                    vlanid=port.vni,
                    vni=seg_id
                )
            )

        for action in actions:
            try:
                resp = requests.put(action,
                                    auth=(self.username, self.password),
                                    verify=False)

                if resp.status_code != requests.codes.ok:
                    msg = (_("Error %(code)d replay to switch %(switch_id)s") %
                           {'code': resp.status_code,
                            'switch_id': switch_id})
                    LOG.info(msg)
                    return resp.status_code

            except requests.exceptions.RequestException as error:
                msg = (_("Error connecting to switch (%(switch_id)s)."
                         " HTTP Error %(error)s") %
                       {'switch_id': switch_id,
                        'error': error})
                LOG.info(msg)

        return requests.codes.ok


class CumulusSwitchSync(object):
    def __init__(self, mech_driver):
        self._mech_driver = mech_driver
        for switch_id in self._mech_driver.switches:
            self._mech_driver.switch_info[switch_id, 'state'] =\
                SwitchState.inactive
            self._mech_driver.switch_info[switch_id, 'hash_id'] =\
                INVALID_HASH_ID
            self._mech_driver.switch_info[switch_id, 'replay'] = True

    def replay_config(self, switch_id):
        all_ports = db.db_get_ports_by_server_id(switch_id)
        for port in all_ports:
            network = db.db_get_network(port.tenant_id, port.network_id)
            if network:
                status = self._mech_driver.replay_to_switch(
                    switch_id,
                    network.bridge_name,
                    port,
                    network.segmentation_id)

                if status != requests.codes.ok:
                    self._mech_driver.switch_info[switch_id, 'replay'] = True

    def check_switch_connections(self):

        for switch_id in self._mech_driver.switches:
            try:
                resp = requests.get(
                    SWITCH_HASH_ID_URL.format(
                        scheme=self._mech_driver.scheme,
                        base=switch_id,
                        port=self._mech_driver.protocol_port
                    ),
                    auth=(self._mech_driver.username,
                          self._mech_driver.password),
                    verify=False
                )

                if resp.status_code != requests.codes.ok:
                    msg = (_("Switch (%(switch_id)s) is unresponsive."
                             " HTTP Error %(error)d") %
                           {'switch_id': switch_id,
                            'error': resp.status_code})
                    LOG.info(msg)
                    self._mech_driver.switch_info[switch_id, 'state'] = \
                        SwitchState.inactive
                    self._mech_driver.switch_info[switch_id, 'replay'] = False
                    self._mech_driver.switch_info[switch_id, 'hash_id'] = \
                        INVALID_HASH_ID
                else:
                    data = resp.json()

                    if data != self._mech_driver.switch_info[switch_id,
                                                             'hash_id']:
                        self._mech_driver.switch_info[switch_id, 'state'] = \
                            SwitchState.active
                        self._mech_driver.switch_info[switch_id, 'replay'] = \
                            True
                        self._mech_driver.switch_info[switch_id, 'hash_id'] = \
                            data

            except requests.exceptions.RequestException:
                self._mech_driver.switch_info[switch_id, 'state'] = \
                    SwitchState.inactive
                self._mech_driver.switch_info[switch_id, 'replay'] = False
                self._mech_driver.switch_info[switch_id, 'hash_id'] = \
                    INVALID_HASH_ID

    def check_and_replay(self):
        self.check_switch_connections()

        for switch_id in self._mech_driver.switches:
            if self._mech_driver.switch_info[switch_id, 'replay']:
                self._mech_driver.switch_info[switch_id, 'replay'] = False
                self.replay_config(switch_id)
