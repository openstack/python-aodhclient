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

import testtools
from unittest import mock

from aodhclient.v2 import metrics_cli


class MetricsTest(testtools.TestCase):
    def setUp(self):
        super().setUp()
        self.app = mock.Mock()
        self.metrics_mgr_mock = self.app.client_manager.alarming.metrics
        self.parser = mock.Mock()
        self.metrics = (
            metrics_cli.CliMetrics(self.app, self.parser))

    def test_metrics(self):
        self.metrics_mgr_mock.get.return_value = {
            "evaluation_results": [
                {
                    "alarm_id": "b8e17f58-089a-43fc-a96b-e9bcac4d4b53",
                    "project_id": "2dd8edd6c8c24f49bf04670534f6b357",
                    "state_counters": {
                        "insufficient data": 1646,
                        "ok": 0,
                        "alarm": 0
                    }
                },
                {
                    "alarm_id": "fa386719-67e3-42ff-aec8-17e547dac77a",
                    "project_id": "2dd8edd6c8c24f49bf04670534f6b357",
                    "state_counters": {
                        "insufficient data": 4,
                        "ok": 923,
                        "alarm": 0
                    }
                },
                {
                    "alarm_id": "0788bf8b-fc1f-4889-b5fd-5acd4d287bc3",
                    "project_id": "d45b070bcce04ca99546128a40854e7c",
                    "state_counters": {
                        "insufficient data": 1646,
                        "ok": 0,
                        "alarm": 0
                    }
                }
            ]
        }
        ret = self.metrics.take_action([])

        self.metrics_mgr_mock.get.assert_called_once_with()
        self.assertIn('name', ret[0])
        self.assertIn('evaluation_result', ret[1][0])
