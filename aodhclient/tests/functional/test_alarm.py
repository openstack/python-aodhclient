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

import os

from oslo_utils import uuidutils
import requests
import requests.auth
from tempest.lib import exceptions

from aodhclient.tests.functional import base


class AodhClientTest(base.ClientTestBase):

    def test_help(self):
        self.aodh("help", params="alarm create")
        self.aodh("help", params="alarm delete")
        self.aodh("help", params="alarm list")
        self.aodh("help", params="alarm show")
        self.aodh("help", params="alarm update")

    def test_alarm_id_or_name_scenario(self):
        def _test(name):
            params = "create --type event --name %s" % name
            result = self.aodh('alarm', params=params)
            alarm_id = self.details_multiple(result)[0]['alarm_id']

            params = 'show %s' % name
            result = self.aodh('alarm', params=params)
            self.assertEqual(alarm_id,
                             self.details_multiple(result)[0]['alarm_id'])

            params = 'show %s' % alarm_id
            result = self.aodh('alarm', params=params)
            self.assertEqual(alarm_id,
                             self.details_multiple(result)[0]['alarm_id'])

            params = "update --state ok %s" % name
            result = self.aodh('alarm', params=params)
            self.assertEqual("ok", self.details_multiple(result)[0]['state'])

            params = "update --state alarm %s" % alarm_id
            result = self.aodh('alarm', params=params)
            self.assertEqual("alarm",
                             self.details_multiple(result)[0]['state'])

            params = "update --name another-name %s" % name
            result = self.aodh('alarm', params=params)
            self.assertEqual("another-name",
                             self.details_multiple(result)[0]['name'])

            params = "update --name %s %s" % (name, alarm_id)
            result = self.aodh('alarm', params=params)
            self.assertEqual(name,
                             self.details_multiple(result)[0]['name'])

            # Check update with no change is allowed
            params = "update --name %s %s" % (name, name)
            result = self.aodh('alarm', params=params)
            self.assertEqual(name,
                             self.details_multiple(result)[0]['name'])

            params = "update --state ok"
            result = self.aodh('alarm', params=params,
                               fail_ok=True, merge_stderr=True)
            self.assertFirstLineStartsWith(
                result.splitlines(),
                'You need to specify one of alarm ID and alarm name(--name) '
                'to update an alarm.')

            params = "delete %s" % name
            result = self.aodh('alarm', params=params)
            self.assertEqual("", result)

            params = "create --type event --name %s" % name
            result = self.aodh('alarm', params=params)
            alarm_id = self.details_multiple(result)[0]['alarm_id']

            params = "delete %s" % alarm_id
            result = self.aodh('alarm', params=params)
            self.assertEqual("", result)

        _test(uuidutils.generate_uuid())
        _test('normal-alarm-name')

    def test_event_scenario(self):

        PROJECT_ID = uuidutils.generate_uuid()

        # CREATE
        result = self.aodh(u'alarm',
                           params=(u"create --type event --name ev_alarm1 "
                                   "--project-id %s" % PROJECT_ID))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('ev_alarm1', alarm['name'])
        self.assertEqual('*', alarm['event_type'])

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

        # GET BY NAME
        result = self.aodh(
            'alarm', params="show --name ev_alarm1")
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('ev_alarm1', alarm_show['name'])
        self.assertEqual('dummy', alarm_show['event_type'])

        # GET BY NAME AND ID ERROR
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"show %s --name ev_alarm1" %
                                  ALARM_ID))

        # LIST
        result = self.aodh('alarm', params="list --filter all_projects=true")
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        output_colums = ['alarm_id', 'type', 'name', 'state', 'severity',
                         'enabled']
        for alarm_list in self.parser.listing(result):
            self.assertEqual(sorted(output_colums), sorted(alarm_list.keys()))
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('ev_alarm1', alarm_list['name'])

        # LIST WITH QUERY
        result = self.aodh('alarm',
                           params=("list --query project_id=%s" % PROJECT_ID))
        alarm_list = self.parser.listing(result)[0]
        self.assertEqual(ALARM_ID, alarm_list["alarm_id"])
        self.assertEqual('ev_alarm1', alarm_list['name'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.assertEqual("", result)

        # GET FAIL
        result = self.aodh('alarm', params="show %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        expected = "Alarm %s not found (HTTP 404)" % ALARM_ID
        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # DELETE FAIL
        result = self.aodh('alarm', params="delete %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # LIST DOES NOT HAVE ALARM
        result = self.aodh('alarm', params="list")
        self.assertNotIn(ALARM_ID,
                         [r['alarm_id'] for r in self.parser.listing(result)])

    def test_composite_scenario(self):

        project_id = uuidutils.generate_uuid()
        res_id = uuidutils.generate_uuid()
        # CREATE
        result = self.aodh(
            u'alarm',
            params=(u'create --type composite --name calarm1 --composite-rule '
                    '\'{"or":[{"threshold": 0.8, "metric": "cpu_util", '
                    '"type": "gnocchi_resources_threshold", "resource_type": '
                    '"generic", "resource_id": "%s", '
                    '"aggregation_method": "mean"},'
                    '{"and": [{"threshold": 200, "metric": "disk.iops", '
                    '"type": "gnocchi_resources_threshold", "resource_type": '
                    '"generic", "resource_id": "%s", '
                    '"aggregation_method": "mean"},'
                    '{"threshold": 1000, "metric": "memory",'
                    '"type": "gnocchi_resources_threshold", "resource_type": '
                    '"generic", "resource_id": "%s", '
                    '"aggregation_method": "mean"}]}]}\' --project-id %s' %
                    (res_id, res_id, res_id, project_id)))
        alarm = self.details_multiple(result)[0]
        alarm_id = alarm['alarm_id']
        self.assertEqual('calarm1', alarm['name'])
        self.assertEqual('composite', alarm['type'])
        self.assertIn('composite_rule', alarm)

        # CREATE FAIL MISSING PARAM
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"create --type composite --name calarm1 "
                                  "--project-id %s" % project_id))

        # UPDATE
        result = self.aodh(
            'alarm', params=("update %s --severity critical" % alarm_id))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(alarm_id, alarm_updated["alarm_id"])
        self.assertEqual('critical', alarm_updated['severity'])

        # GET
        result = self.aodh(
            'alarm', params="show %s" % alarm_id)
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(alarm_id, alarm_show["alarm_id"])
        self.assertEqual(project_id, alarm_show["project_id"])
        self.assertEqual('calarm1', alarm_show['name'])

        # GET BY NAME
        result = self.aodh(
            'alarm', params="show --name calarm1")
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(alarm_id, alarm_show["alarm_id"])
        self.assertEqual(project_id, alarm_show["project_id"])
        self.assertEqual('calarm1', alarm_show['name'])

        # GET BY NAME AND ID ERROR
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"show %s --name calarm1" %
                                  alarm_id))

        # LIST
        result = self.aodh('alarm', params="list --filter all_projects=true")
        self.assertIn(alarm_id,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        output_colums = ['alarm_id', 'type', 'name', 'state', 'severity',
                         'enabled']
        for alarm_list in self.parser.listing(result):
            self.assertEqual(sorted(output_colums), sorted(alarm_list.keys()))
            if alarm_list["alarm_id"] == alarm_id:
                self.assertEqual('calarm1', alarm_list['name'])

        # LIST WITH QUERY
        result = self.aodh('alarm',
                           params=("list --query project_id=%s" % project_id))
        alarm_list = self.parser.listing(result)[0]
        self.assertEqual(alarm_id, alarm_list["alarm_id"])
        self.assertEqual('calarm1', alarm_list['name'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % alarm_id)
        self.assertEqual("", result)

        # GET FAIL
        result = self.aodh('alarm', params="show %s" % alarm_id,
                           fail_ok=True, merge_stderr=True)
        expected = "Alarm %s not found (HTTP 404)" % alarm_id
        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # DELETE FAIL
        result = self.aodh('alarm', params="delete %s" % alarm_id,
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # LIST DOES NOT HAVE ALARM
        result = self.aodh('alarm', params="list")
        self.assertNotIn(alarm_id,
                         [r['alarm_id'] for r in self.parser.listing(result)])

    def _test_alarm_create_show_query(self, create_params, expected_lines):

        def test(params):
            result = self.aodh('alarm', params=params)
            alarm = self.details_multiple(result)[0]
            for key, value in expected_lines.items():
                self.assertEqual(value, alarm[key])
            return alarm

        alarm = test(create_params)
        params = 'show %s' % alarm['alarm_id']
        test(params)
        self.aodh('alarm', params='delete %s' % alarm['alarm_id'])

    def test_event_alarm_create_show_query(self):
        params = ('create --type event --name alarm-multiple-query '
                  '--query "traits.project_id=789;traits.resource_id=012"')
        expected_lines = {
            'query': 'traits.project_id = 789 AND',
            '': 'traits.resource_id = 012',
        }
        self._test_alarm_create_show_query(params, expected_lines)

        params = ('create --type event --name alarm-single-query '
                  '--query "traits.project_id=789"')
        expected_lines = {'query': 'traits.project_id = 789'}
        self._test_alarm_create_show_query(params, expected_lines)

        params = 'create --type event --name alarm-no-query'
        self._test_alarm_create_show_query(params, {'query': ''})

    def test_set_get_alarm_state(self):
        result = self.aodh(
            'alarm',
            params=('create --type event --name alarm_state_test '
                    '--query "traits.project_id=789;traits.resource_id=012"'))
        alarm = self.details_multiple(result)[0]
        alarm_id = alarm['alarm_id']
        result = self.aodh(
            'alarm', params="show %s" % alarm_id)
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual('insufficient data', alarm_show['state'])
        result = self.aodh('alarm', params="state get %s" % alarm_id)
        state_get = self.details_multiple(result)[0]
        self.assertEqual('insufficient data', state_get['state'])
        self.aodh('alarm',
                  params="state set --state ok  %s" % alarm_id)
        result = self.aodh('alarm', params="state get %s" % alarm_id)
        state_get = self.details_multiple(result)[0]
        self.assertEqual('ok', state_get['state'])
        self.aodh('alarm', params='delete %s' % alarm_id)

    def test_update_type_event_composite(self):

        res_id = uuidutils.generate_uuid()
        # CREATE
        result = self.aodh(u'alarm',
                           params=(u"create --type event --name ev_alarm123"))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('ev_alarm123', alarm['name'])
        self.assertEqual('*', alarm['event_type'])

        # UPDATE TYPE TO COMPOSITE
        result = self.aodh(
            'alarm',
            params=('update %s --type composite --composite-rule '
                    '\'{"or":[{"threshold": 0.8, "metric": "cpu_util", '
                    '"type": "gnocchi_resources_threshold", "resource_type": '
                    '"generic", "resource_id": "%s", '
                    '"aggregation_method": "mean"},'
                    '{"and": [{"threshold": 200, "metric": "disk.iops", '
                    '"type": "gnocchi_resources_threshold", "resource_type": '
                    '"generic", "resource_id": "%s", '
                    '"aggregation_method": "mean"},'
                    '{"threshold": 1000, "metric": "memory",'
                    '"type": "gnocchi_resources_threshold", "resource_type": '
                    '"generic", "resource_id": "%s", '
                    '"aggregation_method": "mean"}]}]}\'' %
                    (ALARM_ID, res_id, res_id, res_id)))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('composite', alarm_updated['type'])
        self.assertIn('composite_rule', alarm_updated)

        # UPDATE TYPE TO EVENT
        result = self.aodh(
            'alarm', params=("update %s --type event"
                             % ALARM_ID))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('event', alarm_updated['type'])
        self.assertEqual('*', alarm_updated['event_type'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.assertEqual("", result)


class AodhClientGnocchiRulesTest(base.ClientTestBase):

    def test_gnocchi_resources_threshold_scenario(self):

        PROJECT_ID = uuidutils.generate_uuid()
        RESOURCE_ID = uuidutils.generate_uuid()

        req = requests.post(
            os.environ.get("GNOCCHI_ENDPOINT") + "/v1/resource/generic",
            auth=requests.auth.HTTPBasicAuth('admin', ''),
            json={
                "id": RESOURCE_ID,
            })
        self.assertEqual(201, req.status_code)

        # CREATE
        result = self.aodh(u'alarm',
                           params=(u"create "
                                   "--type gnocchi_resources_threshold "
                                   "--name alarm_gn1 --metric cpu_util "
                                   "--threshold 80 "
                                   "--resource-id %s --resource-type generic "
                                   "--aggregation-method last "
                                   "--project-id %s"
                                   % (RESOURCE_ID, PROJECT_ID)))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('alarm_gn1', alarm['name'])
        self.assertEqual('cpu_util', alarm['metric'])
        self.assertEqual('80.0', alarm['threshold'])
        self.assertEqual('last', alarm['aggregation_method'])
        self.assertEqual(RESOURCE_ID,
                         alarm['resource_id'])
        self.assertEqual('generic', alarm['resource_type'])

        # CREATE WITH --TIME-CONSTRAINT
        result = self.aodh(
            u'alarm',
            params=(u"create --type gnocchi_resources_threshold "
                    "--name alarm_tc --metric cpu_util --threshold 80 "
                    "--resource-id %s --resource-type generic "
                    "--aggregation-method last --project-id %s "
                    "--time-constraint "
                    "name=cons1;start='0 11 * * *';duration=300 "
                    "--time-constraint "
                    "name=cons2;start='0 23 * * *';duration=600 "
                    % (RESOURCE_ID, PROJECT_ID)))
        alarm = self.details_multiple(result)[0]
        self.assertEqual('alarm_tc', alarm['name'])
        self.assertEqual('80.0', alarm['threshold'])
        self.assertIsNotNone(alarm['time_constraints'])

        # CREATE FAIL MISSING PARAM
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"create "
                                  "--type gnocchi_resources_threshold "
                                  "--name alarm1 --metric cpu_util "
                                  "--resource-id %s --resource-type generic "
                                  "--aggregation-method last "
                                  "--project-id %s"
                                  % (RESOURCE_ID, PROJECT_ID)))

        # UPDATE
        result = self.aodh(
            'alarm', params=("update %s --severity critical --threshold 90"
                             % ALARM_ID))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('critical', alarm_updated['severity'])
        self.assertEqual('90.0', alarm_updated["threshold"])

        # GET
        result = self.aodh(
            'alarm', params="show %s" % ALARM_ID)
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('alarm_gn1', alarm_show['name'])
        self.assertEqual('cpu_util', alarm_show['metric'])
        self.assertEqual('90.0', alarm_show['threshold'])
        self.assertEqual('critical', alarm_show['severity'])
        self.assertEqual('last', alarm_show['aggregation_method'])
        self.assertEqual('generic', alarm_show['resource_type'])

        # GET BY NAME
        result = self.aodh(
            'alarm', params="show --name alarm_gn1")
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('alarm_gn1', alarm_show['name'])
        self.assertEqual('cpu_util', alarm_show['metric'])
        self.assertEqual('90.0', alarm_show['threshold'])
        self.assertEqual('critical', alarm_show['severity'])
        self.assertEqual('last', alarm_show['aggregation_method'])
        self.assertEqual('generic', alarm_show['resource_type'])

        # GET BY NAME AND ID ERROR
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"show %s --name alarm_gn1" %
                                  ALARM_ID))

        # LIST
        result = self.aodh('alarm', params="list --filter all_projects=true")
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        output_colums = ['alarm_id', 'type', 'name', 'state', 'severity',
                         'enabled']
        for alarm_list in self.parser.listing(result):
            self.assertEqual(sorted(output_colums), sorted(alarm_list.keys()))
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('alarm_gn1', alarm_list['name'])

        # LIST WITH PAGINATION
        # list with limit
        result = self.aodh('alarm',
                           params="list --filter all_projects=true --limit 1")
        alarm_list = self.parser.listing(result)
        self.assertEqual(1, len(alarm_list))
        # list with sort with key=name dir=asc
        result = self.aodh(
            'alarm',
            params="list --filter all_projects=true --sort name:asc")
        names = [r['name'] for r in self.parser.listing(result)]
        sorted_name = sorted(names)
        self.assertEqual(sorted_name, names)
        # list with sort with key=name dir=asc and key=alarm_id dir=asc
        result = self.aodh(
            u'alarm',
            params=(u"create --type gnocchi_resources_threshold "
                    "--name alarm_th --metric cpu_util --threshold 80 "
                    "--resource-id %s --resource-type generic "
                    "--aggregation-method last --project-id %s "
                    % (RESOURCE_ID, PROJECT_ID)))
        created_alarm_id = self.details_multiple(result)[0]['alarm_id']
        result = self.aodh(
            'alarm',
            params="list --filter all_projects=true --sort name:asc "
                   "--sort alarm_id:asc")
        alarm_list = self.parser.listing(result)
        ids_with_same_name = []
        names = []
        for alarm in alarm_list:
            names.append(['alarm_name'])
            if alarm['name'] == 'alarm_th':
                ids_with_same_name.append(alarm['alarm_id'])
        sorted_ids = sorted(ids_with_same_name)
        sorted_names = sorted(names)
        self.assertEqual(sorted_names, names)
        self.assertEqual(sorted_ids, ids_with_same_name)
        # list with sort with key=name dir=desc and with the marker equal to
        # the alarm_id of the alarm_th we created for this test.
        result = self.aodh(
            'alarm',
            params="list --filter all_projects=true --sort name:desc "
                   "--marker %s" % created_alarm_id)
        self.assertIn('alarm_tc',
                      [r['name'] for r in self.parser.listing(result)])
        self.aodh('alarm', params="delete %s" % created_alarm_id)

        # LIST WITH QUERY
        result = self.aodh('alarm',
                           params=("list --query project_id=%s" % PROJECT_ID))
        alarm_list = self.parser.listing(result)[0]
        self.assertEqual(ALARM_ID, alarm_list["alarm_id"])
        self.assertEqual('alarm_gn1', alarm_list['name'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.assertEqual("", result)

        # GET FAIL
        result = self.aodh('alarm', params="show %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        expected = "Alarm %s not found (HTTP 404)" % ALARM_ID
        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # DELETE FAIL
        result = self.aodh('alarm', params="delete %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # LIST DOES NOT HAVE ALARM
        result = self.aodh('alarm', params="list")
        self.assertNotIn(ALARM_ID,
                         [r['alarm_id'] for r in self.parser.listing(result)])

    def test_gnocchi_aggr_by_resources_scenario(self):

        PROJECT_ID = uuidutils.generate_uuid()

        # CREATE
        result = self.aodh(
            u'alarm',
            params=(u"create "
                    "--type "
                    "gnocchi_aggregation_by_resources_threshold "
                    "--name alarm1 --metric cpu --threshold 80 "
                    "--query "
                    '\'{"=": {"creator": "cr3at0r"}}\' '
                    "--resource-type generic "
                    "--aggregation-method mean "
                    "--project-id %s" % PROJECT_ID))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('alarm1', alarm['name'])
        self.assertEqual('cpu', alarm['metric'])
        self.assertEqual('80.0', alarm['threshold'])
        self.assertEqual('mean', alarm['aggregation_method'])
        self.assertEqual('generic', alarm['resource_type'])
        self.assertEqual('{"=": {"creator": "cr3at0r"}}',
                         alarm['query'])

        # CREATE FAIL MISSING PARAM
        self.assertRaises(
            exceptions.CommandFailed,
            self.aodh, u'alarm',
            params=(u"create "
                    "--type "
                    "gnocchi_aggregation_by_resources_threshold "
                    "--name alarm1 --metric cpu "
                    "--query "
                    '\'{"=": {"creator": "cr3at0r"}}\' '
                    "--resource-type generic "
                    "--aggregation-method mean "
                    "--project-id %s" % PROJECT_ID))

        # UPDATE
        result = self.aodh(
            'alarm', params=("update %s --severity critical --threshold 90"
                             % ALARM_ID))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('critical', alarm_updated['severity'])
        self.assertEqual('90.0', alarm_updated["threshold"])

        # GET
        result = self.aodh(
            'alarm', params="show %s" % ALARM_ID)
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('alarm1', alarm_show['name'])
        self.assertEqual('cpu', alarm_show['metric'])
        self.assertEqual('90.0', alarm_show['threshold'])
        self.assertEqual('critical', alarm_show['severity'])
        self.assertEqual('mean', alarm_show['aggregation_method'])
        self.assertEqual('generic', alarm_show['resource_type'])

        # LIST
        result = self.aodh('alarm', params="list --filter all_projects=true")
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        output_colums = ['alarm_id', 'type', 'name', 'state', 'severity',
                         'enabled']
        for alarm_list in self.parser.listing(result):
            self.assertEqual(sorted(output_colums), sorted(alarm_list.keys()))
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('alarm1', alarm_list['name'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.assertEqual("", result)

        # GET FAIL
        result = self.aodh('alarm', params="show %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        expected = "Alarm %s not found (HTTP 404)" % ALARM_ID
        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # DELETE FAIL
        result = self.aodh('alarm', params="delete %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # LIST DOES NOT HAVE ALARM
        result = self.aodh('alarm', params="list")
        self.assertNotIn(ALARM_ID,
                         [r['alarm_id'] for r in self.parser.listing(result)])

    def test_gnocchi_aggr_by_metrics_scenario(self):

        PROJECT_ID = uuidutils.generate_uuid()
        METRIC1 = 'cpu'
        METRIC2 = 'cpu_util'

        # CREATE
        result = self.aodh(
            u'alarm',
            params=(u"create "
                    "--type gnocchi_aggregation_by_metrics_threshold "
                    "--name alarm1 "
                    "--metrics %s "
                    "--metric %s "
                    "--threshold 80 "
                    "--aggregation-method last "
                    "--project-id %s"
                    % (METRIC1, METRIC2, PROJECT_ID)))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('alarm1', alarm['name'])
        metrics = "['cpu', 'cpu_util']"
        self.assertEqual(metrics, alarm['metrics'])
        self.assertEqual('80.0', alarm['threshold'])
        self.assertEqual('last', alarm['aggregation_method'])

        # CREATE FAIL MISSING PARAM
        self.assertRaises(
            exceptions.CommandFailed,
            self.aodh, u'alarm',
            params=(u"create "
                    "--type gnocchi_aggregation_by_metrics_threshold "
                    "--name alarm1 "
                    "--metrics %s "
                    "--metrics %s "
                    "--aggregation-method last "
                    "--project-id %s"
                    % (METRIC1, METRIC2, PROJECT_ID)))

        # UPDATE
        result = self.aodh(
            'alarm', params=("update %s --severity critical --threshold 90"
                             % ALARM_ID))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('critical', alarm_updated['severity'])
        self.assertEqual('90.0', alarm_updated["threshold"])

        # GET
        result = self.aodh(
            'alarm', params="show %s" % ALARM_ID)
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('alarm1', alarm_show['name'])
        self.assertEqual(metrics, alarm_show['metrics'])
        self.assertEqual('90.0', alarm_show['threshold'])
        self.assertEqual('critical', alarm_show['severity'])
        self.assertEqual('last', alarm_show['aggregation_method'])

        # LIST
        result = self.aodh('alarm', params="list --filter all_projects=true")
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        for alarm_list in self.parser.listing(result):
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('alarm1', alarm_list['name'])

        # LIST WITH QUERY
        result = self.aodh('alarm',
                           params=("list --query project_id=%s" % PROJECT_ID))
        alarm_list = self.parser.listing(result)[0]
        self.assertEqual(ALARM_ID, alarm_list["alarm_id"])
        self.assertEqual('alarm1', alarm_list['name'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.assertEqual("", result)

        # GET FAIL
        result = self.aodh('alarm', params="show %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)
        expected = "Alarm %s not found (HTTP 404)" % ALARM_ID
        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # DELETE FAIL
        result = self.aodh('alarm', params="delete %s" % ALARM_ID,
                           fail_ok=True, merge_stderr=True)

        self.assertFirstLineStartsWith(result.splitlines(), expected)

        # LIST DOES NOT HAVE ALARM
        result = self.aodh('alarm', params="list")
        output_colums = ['alarm_id', 'type', 'name', 'state', 'severity',
                         'enabled']
        for alarm_list in self.parser.listing(result):
            self.assertEqual(sorted(output_colums), sorted(alarm_list.keys()))
        self.assertNotIn(ALARM_ID,
                         [r['alarm_id'] for r in self.parser.listing(result)])

    def test_update_gnresthr_gnaggrresthr(self):

        RESOURCE_ID = uuidutils.generate_uuid()
        # CREATE
        result = self.aodh(u'alarm',
                           params=(u"create "
                                   "--type gnocchi_resources_threshold "
                                   "--name alarm_gn123 --metric cpu_util "
                                   "--resource-id %s --threshold 80 "
                                   "--resource-type generic "
                                   "--aggregation-method last "
                                   % RESOURCE_ID))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('alarm_gn123', alarm['name'])
        self.assertEqual('cpu_util', alarm['metric'])
        self.assertEqual('80.0', alarm['threshold'])
        self.assertEqual('last', alarm['aggregation_method'])
        self.assertEqual('generic', alarm['resource_type'])

        # UPDATE TYPE TO GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD
        result = self.aodh(
            'alarm', params=("update %s --type "
                             "gnocchi_aggregation_by_resources_threshold "
                             "--metric cpu --threshold 90 "
                             "--query "
                             '\'{"=": {"creator": "cr3at0r"}}\' '
                             "--resource-type generic "
                             "--aggregation-method mean "
                             % ALARM_ID))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('cpu', alarm_updated['metric'])
        self.assertEqual('90.0', alarm_updated['threshold'])
        self.assertEqual('mean', alarm_updated['aggregation_method'])
        self.assertEqual('generic', alarm_updated['resource_type'])
        self.assertEqual('{"=": {"creator": "cr3at0r"}}',
                         alarm_updated['query'])
        self.assertEqual('gnocchi_aggregation_by_resources_threshold',
                         alarm_updated['type'])

        # UPDATE TYPE TO GNOCCHI_RESOURCES_THRESHOLD
        result = self.aodh(
            'alarm', params=("update %s "
                             "--type gnocchi_resources_threshold "
                             "--metric cpu_util "
                             "--resource-id %s --threshold 80 "
                             "--resource-type generic "
                             "--aggregation-method last "
                             % (ALARM_ID, RESOURCE_ID)))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('cpu_util', alarm_updated['metric'])
        self.assertEqual('80.0', alarm_updated['threshold'])
        self.assertEqual('last', alarm_updated['aggregation_method'])
        self.assertEqual('generic', alarm_updated['resource_type'])
        self.assertEqual('gnocchi_resources_threshold',
                         alarm_updated['type'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.assertEqual("", result)

    def test_update_gnaggrresthr_gnaggrmetricthr(self):

        METRIC1 = 'cpu'
        METRIC2 = 'cpu_util'

        # CREATE
        result = self.aodh(
            u'alarm',
            params=(u"create "
                    "--type "
                    "gnocchi_aggregation_by_resources_threshold "
                    "--name alarm123 --metric cpu --threshold 80 "
                    "--query "
                    '\'{"=": {"creator": "cr3at0r"}}\' '
                    "--resource-type generic "
                    "--aggregation-method mean "))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('alarm123', alarm['name'])
        self.assertEqual('cpu', alarm['metric'])
        self.assertEqual('80.0', alarm['threshold'])
        self.assertEqual('mean', alarm['aggregation_method'])
        self.assertEqual('generic', alarm['resource_type'])
        self.assertEqual('{"=": {"creator": "cr3at0r"}}',
                         alarm['query'])

        # UPDATE TYPE TO GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD
        result = self.aodh(
            'alarm', params=("update %s --type "
                             "gnocchi_aggregation_by_metrics_threshold "
                             "--metrics %s "
                             "--metrics %s "
                             "--threshold 80 "
                             "--aggregation-method last"
                             % (ALARM_ID, METRIC1, METRIC2)))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        metrics = "['cpu', 'cpu_util']"
        self.assertEqual(metrics, alarm_updated['metrics'])
        self.assertEqual('80.0', alarm_updated['threshold'])
        self.assertEqual('last', alarm_updated['aggregation_method'])
        self.assertEqual('gnocchi_aggregation_by_metrics_threshold',
                         alarm_updated['type'])

        # UPDATE TYPE TO GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD
        result = self.aodh(
            'alarm', params=("update %s --type "
                             "gnocchi_aggregation_by_resources_threshold "
                             "--metric cpu --threshold 80 "
                             "--query "
                             '\'{"=": {"creator": "cr3at0r"}}\' '
                             "--resource-type generic "
                             "--aggregation-method mean "
                             % ALARM_ID))
        alarm_updated = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_updated["alarm_id"])
        self.assertEqual('cpu', alarm_updated['metric'])
        self.assertEqual('80.0', alarm_updated['threshold'])
        self.assertEqual('mean', alarm_updated['aggregation_method'])
        self.assertEqual('generic', alarm_updated['resource_type'])
        self.assertEqual('{"=": {"creator": "cr3at0r"}}',
                         alarm_updated['query'])
        self.assertEqual('gnocchi_aggregation_by_resources_threshold',
                         alarm_updated['type'])

        # DELETE
        result = self.aodh('alarm', params="delete %s" % ALARM_ID)
        self.assertEqual("", result)
