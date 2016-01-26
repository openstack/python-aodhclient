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
from cliff import command
from cliff import lister
from cliff import show
from oslo_serialization import jsonutils
from oslo_utils import strutils

from aodhclient import utils

ALARM_TYPES = ['threshold', 'event', 'composite',
               'gnocchi_resources_threshold',
               'gnocchi_aggregation_by_metrics_threshold',
               'gnocchi_aggregation_by_resources_threshold']
ALARM_STATES = ['ok', 'alarm', 'insufficient data']
ALARM_SEVERITY = ['low', 'moderate', 'critical']
ALARM_OPERATORS = ['lt', 'le', 'eq', 'ne', 'ge', 'gt']
STATISTICS = ['max', 'min', 'avg', 'sum', 'count']

ALARM_LIST_COLS = ['alarm_id', 'type', 'name', 'state', 'severity', 'enabled']


class CliAlarmList(lister.Lister):
    """List alarms"""

    def get_parser(self, prog_name):
        parser = super(CliAlarmList, self).get_parser(prog_name)
        parser.add_argument('-t', '--type', required=True,
                            choices=ALARM_TYPES, help='Type of alarm')
        return parser

    def take_action(self, parsed_args):
        alarms = self.app.client.alarm.list(alarm_type=parsed_args.type)
        return utils.list2cols(ALARM_LIST_COLS, alarms)


class CliAlarmSearch(CliAlarmList):
    """Search alarms with specified query rules"""

    def get_parser(self, prog_name):
        parser = super(CliAlarmSearch, self).get_parser(prog_name)
        parser.add_argument("--query", help="Query"),
        return parser

    def take_action(self, parsed_args):
        type_query = '{"=": {"type": "%s"}}' % parsed_args.type
        if parsed_args.query:
            query = '{"and": [%s, %s]}' % (type_query, parsed_args.query)
        else:
            query = type_query
        alarms = self.app.client.alarm.search(query=query)
        return utils.list2cols(ALARM_LIST_COLS, alarms)


def _format_alarm(alarm):
    if alarm.get('composite_rule'):
        composite_rule = jsonutils.dumps(alarm['composite_rule'], indent=2)
        alarm['composite_rule'] = composite_rule
        return alarm
    for alarm_type in ALARM_TYPES:
        if alarm.get('%s_rule' % alarm_type):
            alarm.update(alarm.pop('%s_rule' % alarm_type))
    return alarm


class CliAlarmShow(show.ShowOne):
    """Show an alarm"""

    def get_parser(self, prog_name):
        parser = super(CliAlarmShow, self).get_parser(prog_name)
        parser.add_argument("alarm_id", help="ID of an alarm")
        return parser

    def take_action(self, parsed_args):
        alarm = self.app.client.alarm.get(alarm_id=parsed_args.alarm_id)
        return self.dict2columns(_format_alarm(alarm))


class CliAlarmCreate(show.ShowOne):
    """Create an alarm"""

    create = True

    def get_parser(self, prog_name):
        parser = super(CliAlarmCreate, self).get_parser(prog_name)
        parser.add_argument('-t', '--type', metavar='<TYPE>',
                            required=self.create,
                            choices=ALARM_TYPES, help='Type of alarm')
        parser.add_argument('--name', metavar='<NAME>', required=self.create,
                            help='Name of the alarm')
        parser.add_argument('--project-id', metavar='<PROJECT_ID>',
                            help='Project to associate with alarm '
                                 '(configurable by admin users only)')
        parser.add_argument('--user-id', metavar='<USER_ID>',
                            help='User to associate with alarm '
                            '(configurable by admin users only)')
        parser.add_argument('--description', metavar='<DESCRIPTION>',
                            help='Free text description of the alarm')
        parser.add_argument('--state', metavar='<STATE>',
                            choices=ALARM_STATES,
                            help='State of the alarm, one of: '
                            + str(ALARM_STATES))
        parser.add_argument('--severity', metavar='<SEVERITY>',
                            choices=ALARM_SEVERITY,
                            help='Severity of the alarm, one of: '
                            + str(ALARM_SEVERITY))
        parser.add_argument('--enabled', type=strutils.bool_from_string,
                            metavar='{True|False}',
                            help=('True if alarm evaluation is enabled'))
        parser.add_argument('--alarm-action', dest='alarm_actions',
                            metavar='<Webhook URL>', action='append',
                            help=('URL to invoke when state transitions to '
                                  'alarm. May be used multiple times'))
        parser.add_argument('--ok-action', dest='ok_actions',
                            metavar='<Webhook URL>', action='append',
                            help=('URL to invoke when state transitions to'
                                  'OK. May be used multiple times'))
        parser.add_argument('--insufficient-data-action',
                            dest='insufficient_data_actions',
                            metavar='<Webhook URL>', action='append',
                            help=('URL to invoke when state transitions to '
                                  'insufficient data. May be used multiple '
                                  'times'))
        parser.add_argument(
            '--time-constraint', dest='time_constraints',
            metavar='<Time Constraint>', action='append',
            help=('Only evaluate the alarm if the time at evaluation '
                  'is within this time constraint. Start point(s) of '
                  'the constraint are specified with a cron expression'
                  ', whereas its duration is given in seconds. '
                  'Can be specified multiple times for multiple '
                  'time constraints, format is: '
                  'name=<CONSTRAINT_NAME>;start=<CRON>;'
                  'duration=<SECONDS>;[description=<DESCRIPTION>;'
                  '[timezone=<IANA Timezone>]]'))
        parser.add_argument('--repeat-actions', dest='repeat_actions',
                            metavar='{True|False}',
                            type=strutils.bool_from_string,
                            help=('True if actions should be repeatedly '
                                  'notified while alarm remains in target '
                                  'state'))

        common_group = parser.add_argument_group('common alarm rules')
        common_group.add_argument(
            '-q', '--query', metavar='<QUERY>', dest='query',
            help='key[op]data_type::value; list. data_type is optional, '
                 'but if supplied must be string, integer, float, or boolean. '
                 'Used by threshold and event alarms')
        common_group.add_argument(
            '--comparison-operator', metavar='<OPERATOR>',
            dest='comparison_operator', choices=ALARM_OPERATORS,
            help='Operator to compare with, one of: ' + str(ALARM_OPERATORS))
        common_group.add_argument(
            '--evaluation-periods', type=int, metavar='<EVAL_PERIODS>',
            dest='evaluation_periods',
            help='Number of periods to evaluate over')
        common_group.add_argument(
            '--threshold', type=float, metavar='<THRESHOLD>',
            dest='threshold', help='Threshold to evaluate against.')
        common_group.add_argument(
            '--metric', metavar='<METRIC>',
            dest='metric', help='Metric to evaluate against.')

        threshold_group = parser.add_argument_group('threshold alarm')
        threshold_group.add_argument(
            '-m', '--meter-name', metavar='<METRIC>',
            dest='meter_name', help='Metric to evaluate against')

        threshold_group.add_argument(
            '--period', type=int, metavar='<PERIOD>', dest='period',
            help='Length of each period (seconds) to evaluate over.')

        threshold_group.add_argument(
            '--statistic', metavar='<STATISTIC>', dest='statistic',
            choices=STATISTICS,
            help='Statistic to evaluate, one of: ' + str(STATISTICS))

        event_group = parser.add_argument_group('event alarm')
        event_group.add_argument(
            '--event-type', metavar='<EVENT_TYPE>',
            dest='event_type', help='Event type to evaluate against')

        gnocchi_common_group = parser.add_argument_group(
            'common gnocchi alarm rules')
        gnocchi_common_group.add_argument(
            '--granularity', metavar='<GRANULARITY>',
            dest='granularity',
            help='The time range in seconds over which to query.')
        gnocchi_common_group.add_argument(
            '--aggregation-method', metavar='<AGGR_METHOD>',
            dest='aggregation_method',
            help='The aggregation_method to compare to the threshold.')

        gnocchi_resource_threshold_group = parser.add_argument_group(
            'gnocchi resource threshold alarm')
        gnocchi_resource_threshold_group.add_argument(
            '--resource-type', metavar='<RESOURCE_TYPE>',
            dest='resource_type', help='The type of resource.')
        gnocchi_resource_threshold_group.add_argument(
            '--resource-id', metavar='<RESOURCE_ID>',
            dest='resource_id', help='The id of a resource.')

        gnocchi_aggr_metrics_group = parser.add_argument_group(
            'gnocchi aggregation by metrics alarm')
        gnocchi_aggr_metrics_group.add_argument(
            '--metrics', metavar='<METRICS>', action='append',
            dest='metrics', help='The list of metric ids.')
        composite_group = parser.add_argument_group('composite alarm')
        composite_group.add_argument(
            '--composite-rule', metavar='<COMPOSITE_RULE>',
            dest='composite_rule',
            type=jsonutils.loads,
            help='Composite threshold rule with JSON format, the form can'
                 'be a nested dict which combine threshold/gnocchi rules by'
                 ' "and", "or". For example, the form is like: '
                 '{"or":[RULE1, RULE2, {"and": [RULE3, RULE4]}]}, The'
                 'RULEx can be basic threshold rules but must include a'
                 '"type" field, like this: {"threshold": 0.8,'
                 '"meter_name":"cpu_util","type":"threshold"}'
        )
        self.parser = parser
        return parser

    def _validate_args(self, parsed_args):
        if (parsed_args.type == 'threshold' and
                not (parsed_args.meter_name and parsed_args.threshold)):
            self.parser.error('threshold alarm requires -m/--meter-name and '
                              '--threshold parameters')
        elif (parsed_args.type == 'gnocchi_resources_threshold' and
              not (parsed_args.metric and parsed_args.threshold and
                   parsed_args.resource_id and parsed_args.resource_type
                   and parsed_args.aggregation_method)):
            self.parser.error('gnocchi_resources_threshold requires --metric, '
                              '--threshold, --resource-id, --resource-type '
                              'and --aggregation-method')
        elif (parsed_args.type == 'gnocchi_aggregation_by_metrics_threshold'
              and not (parsed_args.metrics and parsed_args.threshold and
                       parsed_args.aggregation_method)):
            self.parser.error('gnocchi_aggregation_by_metrics_threshold '
                              'requires --metrics, --threshold and '
                              '--aggregation-method')
        elif (parsed_args.type == 'gnocchi_aggregation_by_resources_threshold'
              and not (parsed_args.metric and parsed_args.threshold and
                       parsed_args.query and parsed_args.resource_type and
                       parsed_args.aggregation_method)):
            self.parser.error('gnocchi_aggregation_by_resources_threshold '
                              'requires --metric, --threshold, '
                              '--aggregation-method, --query and '
                              '--resource_type')
        elif (parsed_args.type == 'composite' and
              not parsed_args.composite_rule):
            self.parser.error('composite alarm requires'
                              ' --composite-rule parameter')

    def _alarm_from_args(self, parsed_args):
        alarm = utils.dict_from_parsed_args(
            parsed_args, ['name', 'project_id', 'user_id', 'description',
                          'state', 'severity', 'enabled', 'alarm_actions',
                          'ok_actions', 'insufficient_data_actions',
                          'time_constraints', 'repeat_actions'])
        alarm['threshold_rule'] = utils.dict_from_parsed_args(
            parsed_args, ['meter_name', 'period', 'evaluation_periods',
                          'statistic', 'comparison_operator', 'threshold',
                          'query'])
        alarm['event_rule'] = utils.dict_from_parsed_args(
            parsed_args, ['event_type', 'query'])
        alarm['gnocchi_resources_threshold_rule'] = (
            utils.dict_from_parsed_args(parsed_args,
                                        ['granularity', 'comparison_operator',
                                         'threshold', 'aggregation_method',
                                         'evaluation_periods', 'metric',
                                         'resource_id', 'resource_type']))
        alarm['gnocchi_aggregation_by_metrics_threshold_rule'] = (
            utils.dict_from_parsed_args(parsed_args,
                                        ['granularity', 'comparison_operator',
                                         'threshold', 'aggregation_method',
                                         'evaluation_periods', 'metrics']))
        alarm['gnocchi_aggregation_by_resources_threshold_rule'] = (
            utils.dict_from_parsed_args(parsed_args,
                                        ['granularity', 'comparison_operator',
                                         'threshold', 'aggregation_method',
                                         'evaluation_periods', 'metric',
                                         'query', 'resource_type']))

        alarm['composite_rule'] = parsed_args.composite_rule
        if self.create:
            alarm['type'] = parsed_args.type
            self._validate_args(parsed_args)
        return alarm

    def take_action(self, parsed_args):
        alarm = self.app.client.alarm.create(
            alarm=self._alarm_from_args(parsed_args))
        return self.dict2columns(_format_alarm(alarm))


class CliAlarmUpdate(CliAlarmCreate):
    """Update an alarm"""

    create = False

    def get_parser(self, prog_name):
        parser = super(CliAlarmUpdate, self).get_parser(prog_name)
        parser.add_argument("alarm_id", help="ID of the alarm")
        return parser

    def take_action(self, parsed_args):
        attributes = self._alarm_from_args(parsed_args)
        updated_alarm = self.app.client.alarm.update(
            alarm_id=parsed_args.alarm_id, alarm_update=attributes)
        return self.dict2columns(_format_alarm(updated_alarm))


class CliAlarmDelete(command.Command):
    """Delete an alarm"""

    def get_parser(self, prog_name):
        parser = super(CliAlarmDelete, self).get_parser(prog_name)
        parser.add_argument("alarm_id", help="ID of the alarm")
        return parser

    def take_action(self, parsed_args):
        self.app.client.alarm.delete(parsed_args.alarm_id)
