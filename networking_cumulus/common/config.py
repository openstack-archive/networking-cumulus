#
# Copyright (c) 2016 Mirantis, Inc.
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

from oslo_config import cfg

from neutron.plugins.common import constants as p_const

# Cumulus Agent related config read from cumulus_agent.ini and neutron.conf.
CUMULUS_OPTS = [
    cfg.StrOpt('tenant_network_types',
               default=[p_const.TYPE_VLAN],
               help='Network type for tenant networks'),
    cfg.IntOpt('report_interval',
               default=30,
               help='Seconds between nodes reporting state to server.'),
    cfg.IntOpt('polling_interval',
               default=2,
               help='The number of seconds the agent will wait between '
                    'polling for local device changes.'),
    cfg.ListOpt('tunnel_types',
                default=[p_const.TYPE_VXLAN],
                help='Tunnel network types supported by the Cumulus Agent.'),
]


def register_options():
    cfg.CONF.register_opts(CUMULUS_OPTS, "CUMULUS")
