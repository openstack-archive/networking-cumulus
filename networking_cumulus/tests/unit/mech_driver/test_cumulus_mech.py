# Copyright 2016 Cumulus Networks
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from neutron.tests.unit import testlib_api

from networking_cumulus.mech_driver import driver as cumulus_driver

TENANT_ID = 'cn_test_tenant_id'
NETWORK_NAME = 'cn_test_network'
NETWORK_ID = 'cn_test_network_id'
VLAN_ID = 1000


class CumulusMechanismDriverTestCase(testlib_api.SqlTestCase):
    """Main test cases for Cumulus Mechanism driver.

    Tests all mechanism driver APIs supported by Cumulus Driver. It invokes
    all the APIs as they would be invoked in real world scenarios and
    verifies the functionality.
    """
    def setUp(self):
        super(CumulusMechanismDriverTestCase, self).setUp()
        cumulus_driver.db = mock.MagicMock()
        self.driver = cumulus_driver.CumulusMechanismDriver()

    def tearDown(self):
        super(CumulusMechanismDriverTestCase, self).tearDown()
        self.driver.stop_sync_thread()

    def test_create_network_precommit(self):
        network_context = self._get_network_context(TENANT_ID,
                                                    NETWORK_ID,
                                                    NETWORK_NAME,
                                                    VLAN_ID,
                                                    False)
        self.driver.create_network_precommit(network_context)
        bridge_name = self.driver.get_bridge_name(NETWORK_ID,
                                                  self.driver.new_bridge)

        expected_calls = [
            mock.call.db_create_network(TENANT_ID,
                                        NETWORK_ID,
                                        VLAN_ID,
                                        bridge_name)
        ]

        cumulus_driver.db.assert_has_calls(expected_calls)

    def test_delete_network_postcommit(self):
        cumulus_driver.db.db_get_bridge_name.return_value = \
            self.driver.get_bridge_name(NETWORK_ID,
                                        self.driver.new_bridge)
        network_context = self._get_network_context(TENANT_ID,
                                                    NETWORK_ID,
                                                    NETWORK_NAME,
                                                    VLAN_ID,
                                                    False)

        self.driver.delete_network_postcommit(network_context)
        expected_calls = [
            mock.call.db_delete_network(TENANT_ID, NETWORK_ID)
        ]

        cumulus_driver.db.assert_has_calls(expected_calls)

    def _get_network_context(self, tenant_id, net_id, net_name,
                             segmentation_id, shared):
        network = {'id': net_id,
                   'tenant_id': tenant_id,
                   'name': net_name,
                   'shared': shared,
                   'provider:network_type': 'vlan',
                   'provider:segmentation_id': segmentation_id}
        network_segments = [{'segmentation_id': segmentation_id,
                             'physical_network': u'default',
                             'id': 'segment-id-for-%s' % segmentation_id,
                             'network_type': 'vlan'}]
        return FakeNetworkContext(tenant_id, network, network_segments,
                                  network)


class FakeNetworkContext(object):
    """To generate network context for testing purposes only."""

    def __init__(self, tenant_id, network, segments=None,
                 original_network=None):
        self._network = network
        self._original_network = original_network
        self._segments = segments

    @property
    def current(self):
        return self._network

    @property
    def original(self):
        return self._original_network

    @property
    def network_segments(self):
        return self._segments
