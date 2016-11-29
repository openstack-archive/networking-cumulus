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

import eventlet
eventlet.monkey_patch()
import sys
import time

from oslo_config import cfg
from oslo_log import log
import oslo_messaging
from oslo_service import loopingcall

from neutron.agent import rpc as agent_rpc
from neutron.common import config as common_config
from neutron.common import topics
from neutron import context

from networking_cumulus._i18n import _, _LE, _LI, _LW
from networking_cumulus.common import config as cumulus_config
from networking_cumulus.common import constants as c_const
from networking_cumulus.ml2.agent import cumulus_agent_rpc
from networking_cumulus.netconf import netconf

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class CumulusAgent(object):

    """Cumulus Agent."""

    target = oslo_messaging.Target(version='1.2')

    def __init__(self):
        self.conf = cfg.CONF
        self.run_check_for_updates = True
        self.use_call = True
        self.hostname = cfg.CONF.host
        self.polling_interval = 1
        self.agent_state = {
            'binary': 'neutron-cumulus-agent',
            'host': self.hostname,
            'topic': topics.AGENT,
            'configurations': {},
            'agent_type': 'Cumulus Agent',
            'start_flag': True}
        self.ensure_integration_bridge_exist()
        self.setup_rpc()

    def check_for_updates(self):
        while self.run_check_for_updates:
            time.sleep(2)

    def start(self):
        LOG.info(_LI("Starting Cumulus Agent."))
        self.setup_report_states()
        t = eventlet.spawn(self.check_for_updates)
        t.wait()

    def stop(self):
        LOG.info(_LI("Stopping Cumulus Agent."))
        self.run_check_for_updates = False
        if self.connection:
            self.connection.close()

    def setup_rpc(self):
        # Ensure that the control exchange is set correctly.
        LOG.info(_LI("Started setting up RPC topics and endpoints."))
        self.agent_id = "neutron-cumulus-agent %s" % self.hostname
        self.topic = topics.AGENT
        self.state_rpc = agent_rpc.PluginReportStateAPI(topics.PLUGIN)

        # RPC network init.
        self.context = context.get_admin_context_without_session()
        # Handle updates from service.
        endpoints = [cumulus_agent_rpc.CumulusAgentRpcCallbacks()]
        # Define the listening consumers for the agent.
        consumers = [
            [c_const.CUMULUS, topics.UPDATE],
        ]
        self.connection = agent_rpc.create_consumers(endpoints,
                                                     self.topic,
                                                     consumers)
        LOG.info(_LI("Finished setting up RPC."))

    def _report_state(self):
        """Reporting agent state to neutron server."""

        try:
            self.state_rpc.report_state(self.context,
                                        self.agent_state,
                                        self.use_call)
            self.use_call = False
            self.agent_state.pop('start_flag', None)
        except Exception:
            LOG.exception(_LE("Heartbeat failure - Failed reporting state!"))

    def setup_report_states(self):
        """Method to send heartbeats to the neutron server."""

        report_interval = CONF.CUMULUS.report_interval
        if report_interval:
            heartbeat = loopingcall.FixedIntervalLoopingCall(
                self._report_state)
            heartbeat.start(interval=report_interval)
        else:
            LOG.warning(_LW("Report interval is not initialized."
                            "Unable to send heartbeats to Neutron Server."))

    def ensure_integration_bridge_exist(self):
        with netconf.ConfFile(netconf.INT_BRIDGE) as cfg:
            cfg.ensure_opt_has_value('bridge-vlan-aware', 'yes')


def main():
    common_config.init(sys.argv[1:])
    common_config.setup_logging()
    cumulus_config.register_options()
    cumulus_agent = CumulusAgent()
    try:
        cumulus_agent.start()
    except Exception as e:
        LOG.exception(_LE("Error in Cumulus agent service."))
        sys.exit(_("ERROR: %s.") % e)
