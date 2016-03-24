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

import uuid

from oslo_serialization import jsonutils

from aodhclient.tests.functional import base


class AlarmHistoryTest(base.ClientTestBase):

    def test_help(self):
        self.aodh("help", params="alarm-history show")
        self.aodh("help", params="alarm-history search")

    def test_alarm_history_scenario(self):

        PROJECT_ID = str(uuid.uuid4())

        result = self.aodh(u'alarm',
                           params=(u"create --type threshold --name history1 "
                                   "-m meter_name --threshold 5 "
                                   "--project-id %s" % PROJECT_ID))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        result = self.aodh(u'alarm',
                           params=(u"create --type threshold --name history2 "
                                   "-m meter_name --threshold 10 "
                                   "--project-id %s" % PROJECT_ID))
        alarm = self.details_multiple(result)[0]
        ALARM_ID2 = alarm['alarm_id']

        # SHOW
        result = self.aodh(
            'alarm-history', params=("show %s" % ALARM_ID))
        history = self.parser.listing(result)[0]
        self.assertEqual('creation', history['type'])
        self.assertEqual('history1',
                         jsonutils.loads(history['detail'])['name'])

        result = self.aodh(
            'alarm-history', params=("show %s" % ALARM_ID2))
        history = self.parser.listing(result)[0]
        self.assertEqual('creation', history['type'])
        self.assertEqual('history2',
                         jsonutils.loads(history['detail'])['name'])

        # SEARCH ALL
        result = self.aodh('alarm-history', params=("search"))
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        self.assertIn(ALARM_ID2,
                      [r['alarm_id'] for r in self.parser.listing(result)])

        # SEARCH
        result = self.aodh('alarm-history',
                           params=("search --query "
                                   "alarm_id=%s"
                                   % ALARM_ID))
        history = self.parser.listing(result)[0]
        self.assertEqual(ALARM_ID, history["alarm_id"])
        self.assertEqual('creation', history['type'])
        self.assertEqual('history1',
                         jsonutils.loads(history['detail'])['name'])

        # CLEANUP
        self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.aodh('alarm', params="delete %s" % ALARM_ID2)
