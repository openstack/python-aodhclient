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

import argparse

import mock
import testtools

from aodhclient.v2 import alarm_cli


class CliAlarmCreateTest(testtools.TestCase):

    def setUp(self):
        super(CliAlarmCreateTest, self).setUp()
        self.app = mock.Mock()
        self.parser = mock.Mock()
        self.cli_alarm_create = (
            alarm_cli.CliAlarmCreate(self.app, self.parser))

    @mock.patch.object(argparse.ArgumentParser, 'error')
    def test_validate_args_gnocchi_resources_threshold(self, mock_arg):
        # Cover the test case of the method _validate_args for
        # gnocchi_resources_threshold
        parser = self.cli_alarm_create.get_parser('aodh alarm create')
        test_parsed_args = parser.parse_args([
            '--name', 'gnocchi_resources_threshold_test',
            '--type', 'gnocchi_resources_threshold',
            '--metric', 'cpu'
            '--aggregation_method', 'last',
            '--resource_type', 'generic',
            '--threshold', '80'
            ])
        self.cli_alarm_create._validate_args(test_parsed_args)
        mock_arg.assert_called_with(
            'gnocchi_resources_threshold requires --metric'
            ', --threshold, --resource-id, --resource-type '
            'and --aggregation-method')

    @mock.patch.object(argparse.ArgumentParser, 'error')
    def test_validate_args_threshold(self, mock_arg):
        # Cover the test case of the method _validate_args for
        # threshold
        parser = self.cli_alarm_create.get_parser('aodh alarm create')
        test_parsed_args = parser.parse_args([
            '--name', 'threshold_test',
            '--type', 'threshold',
            '--threshold', '80'
            ])
        self.cli_alarm_create._validate_args(test_parsed_args)
        mock_arg.assert_called_with(
            'threshold alarm requires -m/--meter-name and '
            '--threshold parameters')

    @mock.patch.object(argparse.ArgumentParser, 'error')
    def test_validate_args_gno_agg_by_resources_threshold(self, mock_arg):
        # Cover the test case of the method _validate_args for
        # gnocchi_aggregation_by_resources_threshold
        parser = self.cli_alarm_create.get_parser('aodh alarm create')
        test_parsed_args = parser.parse_args([
            '--name', 'gnocchi_aggregation_by_resources_threshold_test',
            '--type', 'gnocchi_aggregation_by_resources_threshold',
            '--metric', 'cpu',
            '--aggregation_method', 'last',
            '--resource_type', 'generic',
            '--threshold', '80'
            ])
        self.cli_alarm_create._validate_args(test_parsed_args)
        mock_arg.assert_called_with(
            'gnocchi_aggregation_by_resources_threshold'
            ' requires --metric, --threshold, '
            '--aggregation-method, --query and'
            ' --resource_type')

    @mock.patch.object(argparse.ArgumentParser, 'error')
    def test_validate_args_gno_agg_by_metrics_threshold(self, mock_arg):
        # Cover the test case of the method _validate_args for
        # gnocchi_aggregation_by_metrics_threshold
        parser = self.cli_alarm_create.get_parser('aodh alarm create')
        test_parsed_args = parser.parse_args([
            '--name', 'gnocchi_aggregation_by_metrics_threshold_test',
            '--type', 'gnocchi_aggregation_by_metrics_threshold',
            '--resource_type', 'generic',
            '--threshold', '80'
            ])
        self.cli_alarm_create._validate_args(test_parsed_args)
        mock_arg.assert_called_with(
            'gnocchi_aggregation_by_metrics_threshold'
            ' requires --metrics, --threshold and '
            '--aggregation-method')

    def test_alarm_from_args(self):
        # The test case to cover the method _alarm_from_args
        parser = self.cli_alarm_create.get_parser('aodh alarm create')
        test_parsed_args = parser.parse_args([
            '--type', 'threshold',
            '--name', 'alarm_from_args_test',
            '--project-id', '01919bbd-8b0e-451c-be28-abe250ae9b1b',
            '--user-id', '01919bbd-8b0e-451c-be28-abe250ae9c1c',
            '--description', 'For Test',
            '--state', 'ok',
            '--severity', 'critical',
            '--enabled', 'True',
            '--alarm-action', 'http://something/alarm',
            '--ok-action', 'http://something/ok',
            '--repeat-action', 'True',
            '--insufficient-data-action',
            'http://something/insufficient',
            '--time-constraint', '',
            '--meter-name', 'cpu',
            '--period', '60',
            '--evaluation-periods', '60',
            '--statistic', 'max',
            '--comparison-operator', 'le',
            '--threshold', '80',
            '--event-type', 'event',
            '--query', '{}',
            '--granularity', '60',
            '--aggregation-method', 'last',
            '--metric', 'cpu',
            '--resource-id', '01919bbd-8b0e-451c-be28-abe250ae9c1c',
            '--resource-type', 'generic'
            ])

        # Output for the test
        alarm = {
            'name': 'alarm_from_args_test',
            'project_id': '01919bbd-8b0e-451c-be28-abe250ae9b1b',
            'user_id': '01919bbd-8b0e-451c-be28-abe250ae9c1c',
            'description': 'For Test',
            'state': 'ok',
            'severity': 'critical',
            'enabled': True,
            'alarm_actions': ['http://something/alarm'],
            'ok_actions': ['http://something/ok'],
            'insufficient_data_actions':
                ['http://something/insufficient'],
            'time_constraints': [''],
            'repeat_actions': True,
            'threshold_rule': {
                'meter_name': 'cpu',
                'period': 60,
                'evaluation_periods': 60,
                'statistic': 'max',
                'comparison_operator': 'le',
                'threshold': 80.0,
                'query': '{}'
                },
            'event_rule': {
                'event_type': 'event',
                'query': '{}'
                },
            'gnocchi_resources_threshold_rule': {
                'granularity': '60',
                'metric': 'cpu',
                'aggregation_method': 'last',
                'evaluation_periods': 60,
                'resource_id': '01919bbd-8b0e-451c-be28-abe250ae9c1c',
                'comparison_operator': 'le',
                'threshold': 80.0,
                'resource_type': 'generic'
                },
            'gnocchi_aggregation_by_metrics_threshold_rule': {
                'granularity': '60',
                'aggregation_method': 'last',
                'evaluation_periods': 60,
                'comparison_operator': 'le',
                'threshold': 80.0
                },
            'gnocchi_aggregation_by_resources_threshold_rule': {
                'granularity': '60',
                'metric': 'cpu',
                'aggregation_method': 'last',
                'evaluation_periods': 60,
                'comparison_operator': 'le',
                'threshold': 80.0,
                'query': '{}',
                'resource_type': 'generic'
                },
            'composite_rule': None,
            'type': 'threshold'
            }
        alarm_rep = self.cli_alarm_create._alarm_from_args(test_parsed_args)
        self.assertEqual(alarm, alarm_rep)
