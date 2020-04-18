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

from aodhclient import exceptions
from aodhclient.v2 import quota_cli


class QuotaShowTest(testtools.TestCase):
    def setUp(self):
        super(QuotaShowTest, self).setUp()
        self.app = mock.Mock()
        self.quota_mgr_mock = self.app.client_manager.alarming.quota
        self.parser = mock.Mock()
        self.quota_show = (
            quota_cli.QuotaShow(self.app, self.parser))

    def test_quota_show(self):
        self.quota_mgr_mock.list.return_value = {
            "project_id": "fake_project",
            "quotas": [
                {
                    "limit": 20,
                    "resource": "alarms"
                }
            ]
        }
        parser = self.quota_show.get_parser('')
        args = parser.parse_args(['--project', 'fake_project'])
        # Something like [('alarms',), (20,)]
        ret = list(self.quota_show.take_action(args))

        self.quota_mgr_mock.list.assert_called_once_with(
            project='fake_project')
        self.assertIn('alarms', ret[0])
        self.assertIn(20, ret[1])


class QuotaSetTest(testtools.TestCase):
    def setUp(self):
        super(QuotaSetTest, self).setUp()
        self.app = mock.Mock()
        self.quota_mgr_mock = self.app.client_manager.alarming.quota
        self.parser = mock.Mock()
        self.quota_set = (
            quota_cli.QuotaSet(self.app, self.parser))

    def test_quota_set(self):
        self.quota_mgr_mock.create.return_value = {
            "project_id": "fake_project",
            "quotas": [
                {
                    "limit": 20,
                    "resource": "alarms"
                }
            ]
        }

        parser = self.quota_set.get_parser('')
        args = parser.parse_args(['fake_project', '--alarm', '20'])
        ret = list(self.quota_set.take_action(args))

        self.quota_mgr_mock.create.assert_called_once_with(
            'fake_project', [{'resource': 'alarms', 'limit': 20}])
        self.assertIn('alarms', ret[0])
        self.assertIn(20, ret[1])

    def test_quota_set_invalid_quota(self):
        parser = self.quota_set.get_parser('')
        args = parser.parse_args(['fake_project', '--alarm', '-2'])

        self.assertRaises(exceptions.CommandError,
                          self.quota_set.take_action,
                          args)
