import json

from oslo_config import cfg
from oslo_log import log as logging
import requests
from requests.exceptions import HTTPError

from neutron.extensions import portbindings
from neutron.i18n import _LE, _LI, _LW
from neutron.plugins.ml2.common.exceptions import MechanismDriverError
from neutron.plugins.ml2.driver_api import MechanismDriver

from mech_driver import config

LOG = logging.getLogger(__name__)
NETWORKS_URL = '{scheme}://{base}:{port}/ml2/v1/networks/{network}'
HOSTS_URL = '{scheme}://{base}:{port}/ml2/v1/networks/{network}/hosts/{host}'
VXLAN_URL = '{scheme}://{base}:{port}/ml2/v1/networks/{network}/vxlan/{vni}'

"""

list of switches is required to be configured. Add this config to the ml2_conf.ini config
switche names or IPs must be separated using comma.

[ml2_cumulus]
switches="192.168.10.10,192.168.20.20"
"""

class CumulusMechanismDriver(MechanismDriver):
    """
    Mechanism driver for Cumulus Linux that manages connectivity between switches
    and (compute) hosts using the Cumulus API
    """
    def initialize(self):
        self.scheme = cfg.CONF.ml2_cumulus.scheme
        self.protocol_port = cfg.CONF.ml2_cumulus.protocol_port
        self.switches = cfg.CONF.ml2_cumulus.switches
        if self.switches:
            LOG.info(_LI('switches found in ml2_conf files %s'), self.switches)
        else:
            LOG.info(_LI('no switches in ml2_conf files'))

    def bind_port(self, context):
        if context.binding_levels:
            return  # we've already got a top binding

        # assign a dynamic vlan
        next_segment = context.allocate_dynamic_segment(
            {'id': context.network.current, 'network_type': 'vlan'}
        )

        context.continue_binding(
            context.segments_to_bind[0]['id'],
            [next_segment]
        )

    def delete_network_postcommit(self, context):
        network_id = context.current['id']
        vni = context.current['provider:segmentation_id']

        # remove vxlan from all hosts - a little unpleasant
        for _switch_ip in self.switches:

            r = requests.delete(
                VXLAN_URL.format(
                    scheme=self.scheme,
                    base=_switch_ip,
                    port=self.protocol_port,
                    network=network_id,
                    vni=vni
                )
            )

            if r.status_code != requests.codes.ok:
                LOG.info(
                    _LI('Error during vxlan delete. HTTP Error:%d'),
                    r.status_code
                )

            r = requests.delete(
                NETWORKS_URL.format(
                    scheme=self.scheme,
                    base=_switch_ip,
                    port=self.protocol_port,
                    network=network_id
                )
            )

            if r.status_code != requests.codes.ok:
                LOG.info(
                    _LI('Error during network delete. HTTP Error:%d'),
                    r.status_code
                )

    def create_port_postcommit(self, context):
        if context.segments_to_bind:
            self._add_to_switch(context)

    def update_port_postcommit(self, context):
        if context.host != context.original_host:
            self._remove_from_switch(context.original)
        self._add_to_switch(context)

    def delete_port_postcommit(self, context):
        self._remove_from_switch(context)

    def _add_to_switch(self, context):
        if not hasattr(context, 'current'):
            return
        port = context.current
        device_id = port['device_id']
        device_owner = port['device_owner']
        host = port[portbindings.HOST_ID]
        network_id = port['network_id']
        if not hasattr(context, 'top_bound_segment'):
            return
        if not context.top_bound_segment:
            return
        vni = context.top_bound_segment['segmentation_id']
        vlan = context.bottom_bound_segment['segmentation_id']

        if not (host and device_id and device_owner):
            return


        for _switch_ip in self.switches:
            r = requests.put(
                NETWORKS_URL.format(
                    scheme=self.scheme,
                    base=_switch_ip,
                    port=self.protocol_port,
                    network=network_id
                ),
                data=json.dumps({'vlan': vlan})
            )

            if r.status_code != requests.codes.ok:
                raise MechanismDriverError()

            actions = [
                HOSTS_URL.format(
                    scheme=self.scheme,
                    base=_switch_ip,
                    port=self.protocol_port,
                    network=network_id,
                    host=host
                ),
            ]
            if context.top_bound_segment != context.bottom_bound_segment:
                actions.append(
                    VXLAN_URL.format(
                        scheme=self.scheme,
                        base=_switch_ip,
                        port=self.protocol_port,
                        network=network_id,
                        vni=vni
                    )
                )


            for action in actions:
                r = requests.put(action)

                if r.status_code != requests.codes.ok:
                    raise MechanismDriverError()

    def _remove_from_switch(self, context):
        if not hasattr(context, 'current'):
            return
        port = context.current
        host = port[portbindings.HOST_ID]
        network_id = port['network_id']

        for _switch_ip in self.switches:

            r = requests.delete(
                HOSTS_URL.format(
                    scheme=self.scheme,
                    base=_switch_ip,
                    port=self.protocol_port,
                    network=network_id,
                    host=host
                )
            )

            if r.status_code != requests.codes.ok:
                LOG.info(
                    _LI('error (%d) deleting port for %s on switch: %s'),
                    r.status_code,
                    host,
                    _switch_ip
                )
