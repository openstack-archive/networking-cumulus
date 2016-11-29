# Copyright 2016 Mirantis, Inc.
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


import unittest

import mock
from neutron.plugins.ml2 import driver_context

from networking_cumulus.ml2.mech_driver import cumulus_mech as cm

class TestCumulusLBAgentMechanismDriver(unittest.TestCase):
    def setUp(self):
        super(TestCumulusLBAgentMechanismDriver, self).setUp()
        self.rpc_mock = mock.Mock()
        patcher = mock.patch('networking_cumulus.ml2.agent.cumulus_agent_rpc.CumulusRpcClientAPI',
                             return_value=self.rpc_mock)
        patcher.start()
        self.addCleanup(patcher.stop)
        

    def test_create_network_postcommit(self):
        driver = cm.CumulusLBAgentMechanismDriver()
        driver.initialize()
        mock_context = mock.create_autospec(driver_context.NetworkContext)
        mock_context.current = {'id': 22,
                                'provider:network_type': 'vlan',
                                'provider:segmentation_id': 22}

        driver.create_network_postcommit(mock_context)
        self.rpc_mock.create_network_cast.assert_called_once_with(
            current=mock_context.current)
