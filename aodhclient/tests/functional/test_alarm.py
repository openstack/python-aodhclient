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
import uuid

import requests
import six
from tempest.lib import exceptions

from aodhclient.tests.functional import base


class AodhClientTest(base.ClientTestBase):

    def test_help(self):
        self.aodh("help", params="alarm create")
        self.aodh("help", params="alarm delete")
        self.aodh("help", params="alarm list")
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
        self.assertFirstLineStartsWith(
            result.splitlines(),
            "Alarm with name='ev_alarm1' exists (HTTP 409)")

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
            'alarm', params="show --alarm-name ev_alarm1")
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('ev_alarm1', alarm_show['name'])
        self.assertEqual('dummy', alarm_show['event_type'])

        # GET BY NAME AND ID ERROR
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"show %s --alarm-name ev_alarm1" %
                                  ALARM_ID))

        # LIST
        result = self.aodh('alarm', params="list")
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

    def test_threshold_scenario(self):

        PROJECT_ID = str(uuid.uuid4())

        # CREATE
        result = self.aodh(u'alarm',
                           params=(u"create --type threshold --name alarm_th "
                                   "-m meter_name --threshold 5 "
                                   "--project-id %s" % PROJECT_ID))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('alarm_th', alarm['name'])
        self.assertEqual('meter_name', alarm['meter_name'])
        self.assertEqual('5.0', alarm['threshold'])

        # CREATE WITH --TIME-CONSTRAINT
        result = self.aodh(
            u'alarm',
            params=(u"create --type threshold --name alarm_tc "
                    "-m meter_name --threshold 5 "
                    "--time-constraint "
                    "name=cons1;start='0 11 * * *';duration=300 "
                    "--time-constraint "
                    "name=cons2;start='0 23 * * *';duration=600 "
                    "--project-id %s" % PROJECT_ID))
        alarm = self.details_multiple(result)[0]
        self.assertEqual('alarm_tc', alarm['name'])
        self.assertEqual('meter_name', alarm['meter_name'])
        self.assertEqual('5.0', alarm['threshold'])
        self.assertIsNotNone(alarm['time_constraints'])

        # CREATE FAIL
        result = self.aodh(u'alarm',
                           params=(u"create --type threshold --name alarm_th "
                                   "-m meter_name --threshold 5 "
                                   "--project-id %s" % PROJECT_ID),
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(
            result.splitlines(),
            "Alarm with name='alarm_th' exists (HTTP 409)")

        # CREATE FAIL MISSING PARAM
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"create --type threshold --name alarm_th "
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
        self.assertEqual('alarm_th', alarm_show['name'])
        self.assertEqual('meter_name', alarm_show['meter_name'])
        self.assertEqual('10.0', alarm_show['threshold'])

        # GET BY NAME
        result = self.aodh(
            'alarm', params="show --alarm-name alarm_th")
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('alarm_th', alarm_show['name'])
        self.assertEqual('meter_name', alarm_show['meter_name'])
        self.assertEqual('10.0', alarm_show['threshold'])

        # GET BY NAME AND ID ERROR
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"show %s --alarm-name alarm_th" %
                                  ALARM_ID))

        # LIST
        result = self.aodh('alarm', params="list")
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        output_colums = ['alarm_id', 'type', 'name', 'state', 'severity',
                         'enabled']
        for alarm_list in self.parser.listing(result):
            self.assertEqual(sorted(output_colums), sorted(alarm_list.keys()))
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('alarm_th', alarm_list['name'])

        # LIST WITH QUERY
        result = self.aodh('alarm',
                           params=("list --query project_id=%s" % PROJECT_ID))
        alarm_list = self.parser.listing(result)[0]
        self.assertEqual(ALARM_ID, alarm_list["alarm_id"])
        self.assertEqual('alarm_th', alarm_list['name'])

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

        project_id = str(uuid.uuid4())
        # CREATE
        result = self.aodh(u'alarm',
                           params=(u'create --type composite --name calarm1 '
                                   ' --composite-rule \'{"or":[{"threshold"'
                                   ': 0.8,"meter_name": "cpu_util",'
                                   '"type": "threshold"},{"and": ['
                                   '{"threshold": 200, "meter_name": '
                                   '"disk.iops", "type": "threshold"},'
                                   '{"threshold": 1000,"meter_name":'
                                   '"network.incoming.packets.rate",'
                                   '"type": "threshold"}]}]}\' '
                                   '--project-id %s' % project_id))
        alarm = self.details_multiple(result)[0]
        alarm_id = alarm['alarm_id']
        self.assertEqual('calarm1', alarm['name'])
        self.assertEqual('composite', alarm['type'])
        self.assertIn('composite_rule', alarm)

        # CREATE FAIL
        result = self.aodh(u'alarm',
                           params=(u'create --type composite --name calarm1 '
                                   ' --composite-rule \'{"or":[{"threshold"'
                                   ': 0.8,"meter_name": "cpu_util",'
                                   '"type": "threshold"},{"and": ['
                                   '{"threshold": 200, "meter_name": '
                                   '"disk.iops", "type": "threshold"},'
                                   '{"threshold": 1000,"meter_name":'
                                   '"network.incoming.packets.rate",'
                                   '"type": "threshold"}]}]}\' '
                                   '--project-id %s' % project_id),
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(
            result.splitlines(), "Alarm with name='calarm1' exists (HTTP 409)")

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
            'alarm', params="show --alarm-name calarm1")
        alarm_show = self.details_multiple(result)[0]
        self.assertEqual(alarm_id, alarm_show["alarm_id"])
        self.assertEqual(project_id, alarm_show["project_id"])
        self.assertEqual('calarm1', alarm_show['name'])

        # GET BY NAME AND ID ERROR
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"show %s --alarm-name calarm1" %
                                  alarm_id))

        # LIST
        result = self.aodh('alarm', params="list")
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


class AodhClientGnocchiRulesTest(base.ClientTestBase):

    def test_gnocchi_resources_threshold_scenario(self):

        PROJECT_ID = str(uuid.uuid4())
        RESOURCE_ID = str(uuid.uuid4())

        req = requests.post(
            os.environ.get("GNOCCHI_ENDPOINT") + "/v1/resource/instance",
            json={
                "display_name": "myvm",
                "flavor_id": "2", "host": "blah",
                "id": RESOURCE_ID,
                "image_ref": "http://image",
                "project_id": "BD3A1E52-1C62-44CB-BF04-660BD88CD74D",
                "user_id": "BD3A1E52-1C62-44CB-BF04-660BD88CD74D",
            })
        self.assertEqual(201, req.status_code)

        # CREATE
        result = self.aodh(u'alarm',
                           params=(u"create "
                                   "--type gnocchi_resources_threshold "
                                   "--name alarm_gn1 --metric cpu_util "
                                   "--threshold 80 "
                                   "--resource-id %s --resource-type instance "
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
        self.assertEqual('instance', alarm['resource_type'])

        # CREATE FAIL
        result = self.aodh(u'alarm',
                           params=(u"create "
                                   "--type gnocchi_resources_threshold "
                                   "--name alarm_gn1 --metric cpu_util "
                                   "--threshold 80 "
                                   "--resource-id %s --resource-type instance "
                                   "--aggregation-method last "
                                   "--project-id %s"
                                   % (RESOURCE_ID, PROJECT_ID)),
                           fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(
            result.splitlines(),
            "Alarm with name='alarm_gn1' exists (HTTP 409)")

        # CREATE FAIL MISSING PARAM
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"create "
                                  "--type gnocchi_resources_threshold "
                                  "--name alarm1 --metric cpu_util "
                                  "--resource-id %s --resource-type instance "
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
        self.assertEqual('instance', alarm_show['resource_type'])

        # GET BY NAME
        result = self.aodh(
            'alarm', params="show --alarm-name alarm_gn1")
        self.assertEqual(ALARM_ID, alarm_show["alarm_id"])
        self.assertEqual(PROJECT_ID, alarm_show["project_id"])
        self.assertEqual('alarm_gn1', alarm_show['name'])
        self.assertEqual('cpu_util', alarm_show['metric'])
        self.assertEqual('90.0', alarm_show['threshold'])
        self.assertEqual('critical', alarm_show['severity'])
        self.assertEqual('last', alarm_show['aggregation_method'])
        self.assertEqual('instance', alarm_show['resource_type'])

        # GET BY NAME AND ID ERROR
        self.assertRaises(exceptions.CommandFailed,
                          self.aodh, u'alarm',
                          params=(u"show %s --alarm-name alarm_gn1" %
                                  ALARM_ID))

        # LIST
        result = self.aodh('alarm', params="list")
        self.assertIn(ALARM_ID,
                      [r['alarm_id'] for r in self.parser.listing(result)])
        output_colums = ['alarm_id', 'type', 'name', 'state', 'severity',
                         'enabled']
        for alarm_list in self.parser.listing(result):
            self.assertEqual(sorted(output_colums), sorted(alarm_list.keys()))
            if alarm_list["alarm_id"] == ALARM_ID:
                self.assertEqual('alarm_gn1', alarm_list['name'])

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

        PROJECT_ID = str(uuid.uuid4())

        # CREATE
        result = self.aodh(
            u'alarm',
            params=(u"create "
                    "--type "
                    "gnocchi_aggregation_by_resources_threshold "
                    "--name alarm1 --metric cpu --threshold 80 "
                    "--query "
                    '\'{"=": {"server_group": "my_group"}}\' '
                    "--resource-type instance "
                    "--aggregation-method last "
                    "--project-id %s" % PROJECT_ID))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('alarm1', alarm['name'])
        self.assertEqual('cpu', alarm['metric'])
        self.assertEqual('80.0', alarm['threshold'])
        self.assertEqual('last', alarm['aggregation_method'])
        self.assertEqual('instance', alarm['resource_type'])
        self.assertEqual('{"=": {"server_group": "my_group"}}',
                         alarm['query'])

        # CREATE FAIL
        result = self.aodh(
            u'alarm',
            params=(u"create "
                    "--type "
                    "gnocchi_aggregation_by_resources_threshold "
                    "--name alarm1 --metric cpu --threshold 80 "
                    "--query "
                    '\'{"=": {"server_group": "my_group"}}\' '
                    "--resource-type instance "
                    "--aggregation-method last "
                    "--project-id %s" % PROJECT_ID),
            fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(
            result.splitlines(), "Alarm with name='alarm1' exists (HTTP 409)")

        # CREATE FAIL MISSING PARAM
        self.assertRaises(
            exceptions.CommandFailed,
            self.aodh, u'alarm',
            params=(u"create "
                    "--type "
                    "gnocchi_aggregation_by_resources_threshold "
                    "--name alarm1 --metric cpu "
                    "--query "
                    '\'{"=": {"server_group": "my_group"}}\' '
                    "--resource-type instance "
                    "--aggregation-method last "
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
        self.assertEqual('last', alarm_show['aggregation_method'])
        self.assertEqual('instance', alarm_show['resource_type'])

        # LIST
        result = self.aodh('alarm', params="list")
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

        PROJECT_ID = str(uuid.uuid4())
        METRIC1 = 'cpu'
        METRIC2 = 'cpu_util'

        # CREATE
        result = self.aodh(
            u'alarm',
            params=(u"create "
                    "--type gnocchi_aggregation_by_metrics_threshold "
                    "--name alarm1 "
                    "--metrics %s "
                    "--metrics %s "
                    "--threshold 80 "
                    "--aggregation-method last "
                    "--project-id %s"
                    % (METRIC1, METRIC2, PROJECT_ID)))
        alarm = self.details_multiple(result)[0]
        ALARM_ID = alarm['alarm_id']
        self.assertEqual('alarm1', alarm['name'])
        metrics = "[u'cpu', u'cpu_util']" if six.PY2 else "['cpu', 'cpu_util']"
        self.assertEqual(metrics, alarm['metrics'])
        self.assertEqual('80.0', alarm['threshold'])
        self.assertEqual('last', alarm['aggregation_method'])

        # CREATE FAIL
        result = self.aodh(
            u'alarm',
            params=(u"create "
                    "--type gnocchi_aggregation_by_metrics_threshold "
                    "--name alarm1 "
                    "--metrics %s "
                    "--metrics %s "
                    "--threshold 80 "
                    "--aggregation-method last "
                    "--project-id %s"
                    % (METRIC1, METRIC2, PROJECT_ID)),
            fail_ok=True, merge_stderr=True)
        self.assertFirstLineStartsWith(
            result.splitlines(), "Alarm with name='alarm1' exists (HTTP 409)")

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
        result = self.aodh('alarm', params="list")
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
