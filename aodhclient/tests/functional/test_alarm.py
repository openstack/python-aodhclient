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

from tempest_lib import exceptions

from aodhclient.tests.functional import base


class AodhClientTest(base.ClientTestBase):

    def test_help(self):
        self.aodh("help", params="alarm create")
        self.aodh("help", params="alarm delete")
        self.aodh("help", params="alarm list")
        self.aodh("help", params="alarm search")
        self.aodh("help", params="alarm show")
        self.aodh("help", params="alarm update")

    def test_event_scenario(self):

        PROJECT_ID = str(uuid.uuid4())

        # CREATE
        result = self.aodh(u'alarm',
                           params=(u"create --type event --name ev_alarm1 "
                                   "--project-id %s" % PROJECT_ID))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('ev_alarm1', alarm['name'])
        self.assertEqual('*', alarm['event_type'])

        # CREATE FAIL
        result = self.aodh(u'alarm',
                           params=(u"create --type event --name ev_alarm1 "
                                   "--project-id %s" % PROJECT_ID),
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.split('\n'),
                                       'Conflict (HTTP 409)')

        # UPDATE IGNORE INVALID
        result = self.aodh(
            'alarm', params=("update %s --severity critical --threshold 10"
                             % ALARM_ID))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('critical', alarm_updated['severity'])

        # UPDATE IGNORE INVALID
        result = self.aodh(
            'alarm', params=("update %s --event-type dummy" % ALARM_ID))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('dummy', alarm_updated['event_type'])

        # GET
        result = self.aodh(
            'alarm', params="show %s" % ALARM_ID)
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('ev_alarm1', alarm_show['name'])
        self.assertEqual('dummy', alarm_show['event_type'])

        # LIST
        result = self.aodh('alarm', params="list --type event")
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        for alarm_list in self.parser.listing(result):
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('ev_alarm1', alarm_list['name'])

        # SEARCH ALL
        result = self.aodh('alarm', params=("search --type event"))
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        for alarm_list in self.parser.listing(result):
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('ev_alarm1', alarm_list['name'])

        # SEARCH SOME
        result = self.aodh('alarm',
                           params=("search --type event --query "
                                   "'{\"=\": {\"project_id\": \"%s\"}}'"
                                   % PROJECT_ID))
        alarm_list = self.parser.listing(result)[0]
        self.assertEqual(ALARM_ID, alarm_list["alarm_id"])
        self.assertEqual('ev_alarm1', alarm_list['name'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.assertEqual("", result)

        # GET FAIL
        result = self.aodh('alarm', params="show %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.split('\n'),
                                       "Not found (HTTP 404)")

        # DELETE FAIL
        result = self.aodh('alarm', params="delete %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.split('\n'),
                                       "Not found (HTTP 404)")

        # LIST DOES NOT HAVE ALARM
        result = self.aodh('alarm', params="list --type event")
        self.assertNotIn(ALARM_ID,
                         [r['alarm_id'] for r in self.parser.listing(result)])

    def test_threshold_scenario(self):

        PROJECT_ID = str(uuid.uuid4())

        # CREATE
        result = self.aodh(u'alarm',
                           params=(u"create --type threshold --name alarm1 "
                                   " -m meter_name --threshold 5 "
                                   "--project-id %s" % PROJECT_ID))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('alarm1', alarm['name'])
        self.assertEqual('meter_name', alarm['meter_name'])
        self.assertEqual('5.0', alarm['threshold'])

        # CREATE FAIL
        result = self.aodh(u'alarm',
                           params=(u"create --type threshold --name alarm1 "
                                   "-m meter_name --threshold 5 "
                                   "--project-id %s" % PROJECT_ID),
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.split('\n'),
                                       'Conflict (HTTP 409)')

        # CREATE FAIL MISSING PARAM
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"create --type threshold --name alarm1 "
                                  "--project-id %s" % PROJECT_ID))

        # UPDATE
        result = self.aodh(
            'alarm', params=("update %s --severity critical --threshold 10"
                             % ALARM_ID))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('critical', alarm_updated['severity'])
        self.assertEqual('10.0', alarm_updated["threshold"])

        # GET
        result = self.aodh(
            'alarm', params="show %s" % ALARM_ID)
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('alarm1', alarm_show['name'])
        self.assertEqual('meter_name', alarm_show['meter_name'])
        self.assertEqual('10.0', alarm_show['threshold'])

        # LIST
        result = self.aodh('alarm', params="list --type threshold")
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        for alarm_list in self.parser.listing(result):
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('alarm1', alarm_list['name'])

        # SEARCH ALL
        result = self.aodh('alarm', params=("search --type threshold"))
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        for alarm_list in self.parser.listing(result):
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('alarm1', alarm_list['name'])

        # SEARCH SOME
        result = self.aodh('alarm',
                           params=("search --type threshold --query "
                                   "'{\"=\": {\"project_id\": \"%s\"}}'"
                                   % PROJECT_ID))
        alarm_list = self.parser.listing(result)[0]
        self.assertEqual(ALARM_ID, alarm_list["alarm_id"])
        self.assertEqual('alarm1', alarm_list['name'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.assertEqual("", result)

        # GET FAIL
        result = self.aodh('alarm', params="show %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.split('\n'),
                                       "Not found (HTTP 404)")

        # DELETE FAIL
        result = self.aodh('alarm', params="delete %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.split('\n'),
                                       "Not found (HTTP 404)")

        # LIST DOES NOT HAVE ALARM
        result = self.aodh('alarm', params="list --type threshold")
        self.assertNotIn(ALARM_ID,
                         [r['alarm_id'] for r in self.parser.listing(result)])
