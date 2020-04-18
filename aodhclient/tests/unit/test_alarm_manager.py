#
#    Copyright IBM 2016. All rights reserved
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

from aodhclient.v2 import alarm


class AlarmManagerTest(testtools.TestCase):

    def setUp(self):
        super(AlarmManagerTest, self).setUp()
        self.client = mock.Mock()
        self.alarms = {
            'event_alarm': {
                'gnocchi_aggregation_by_metrics_threshold_rule': {},
                'gnocchi_resources_threshold_rule': {},
                'name': 'event_alarm',
                'gnocchi_aggregation_by_resources_threshold_rule': {},
                'event_rule': {},
                'type': 'event'}
        }
        self.results = {
            "result1": {
                "event_rule": {}
            },
        }

    @mock.patch.object(alarm.AlarmManager, '_get')
    def test_list(self, mock_am):
        am = alarm.AlarmManager(self.client)
        am.list()
        mock_am.assert_called_with('v2/alarms')

    @mock.patch.object(alarm.AlarmManager, '_post')
    def test_query(self, mock_am):
        am = alarm.AlarmManager(self.client)
        query = '{"=": {"type": "event"}}'
        am.query(query)
        url = 'v2/query/alarms'
        expected_value = ('{"filter": "{\\"=\\": {\\"type\\":'
                          ' \\"event\\"}}"}')
        headers_value = {'Content-Type': "application/json"}
        mock_am.assert_called_with(
            url,
            data=expected_value,
            headers=headers_value)

    @mock.patch.object(alarm.AlarmManager, '_get')
    def test_list_with_filters(self, mock_am):
        am = alarm.AlarmManager(self.client)
        filters = dict(type='gnocchi_resources_threshold', severity='low')
        am.list(filters=filters)
        expected_url = (
            "v2/alarms?q.field=severity&q.op=eq&q.value=low&"
            "q.field=type&q.op=eq&q.value=gnocchi_resources_threshold")
        mock_am.assert_called_with(expected_url)

    @mock.patch.object(alarm.AlarmManager, '_get')
    def test_get(self, mock_am):
        am = alarm.AlarmManager(self.client)
        am.get('01919bbd-8b0e-451c-be28-abe250ae9b1b')
        mock_am.assert_called_with(
            'v2/alarms/01919bbd-8b0e-451c-be28-abe250ae9b1b')

    @mock.patch.object(alarm.AlarmManager, '_delete')
    def test_delete(self, mock_am):
        am = alarm.AlarmManager(self.client)
        am.delete('01919bbd-8b0e-451c-be28-abe250ae9b1b')
        mock_am.assert_called_with(
            'v2/alarms/01919bbd-8b0e-451c-be28-abe250ae9b1b')

    def test_clean_rules_event_alarm(self):
        am = alarm.AlarmManager(self.client)
        alarm_value = self.alarms.get('event_alarm')
        am._clean_rules('event', alarm_value)
        alarm_value.pop('type')
        alarm_value.pop('name')
        result = self.results.get("result1")
        self.assertEqual(alarm_value, result)
