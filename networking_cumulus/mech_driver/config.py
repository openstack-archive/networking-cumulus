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

from oslo_config import cfg

from networking_cumulus._i18n import _

CUMULUS_DRIVER_OPTS = [
    cfg.StrOpt('scheme',
               default='https',
               help=_('Scheme for base URL for the Cumulus ML2 API')),
    cfg.IntOpt('protocol_port',
               default='8080',
               help=_('Protocol port for base URL for the Cumulus ML2 API')),
    cfg.StrOpt('username',
               default='cumulus',
               help=_('username for Cumulus switch')),
    cfg.StrOpt('password',
               default='CumulusLinux!',
               help=_('password for Cumulus switch')),
    cfg.ListOpt('switches', default=[],
                help=_('list of switch name/ip and remote switch port '
                       'connected to this compute node')),
    cfg.IntOpt('sync_time', default=30,
               help=_('Periodic time interval for checking connection with '
                      'switch. (0=no syncing)')),
    cfg.BoolOpt('spf_enable', default=False,
                help=_('SPF configuration for the bridge')),
    cfg.BoolOpt('new_bridge', default=False,
                help=_('Bridge model used for configuration'))
]

cfg.CONF.register_opts(CUMULUS_DRIVER_OPTS, 'ml2_cumulus')
