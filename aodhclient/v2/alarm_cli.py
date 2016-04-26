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

from cliff import command
from cliff import lister
from cliff import show
from oslo_serialization import jsonutils
from oslo_utils import strutils

from aodhclient import exceptions
from aodhclient.i18n import _
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

    @staticmethod
    def split_filter_param(param):
        key, eq_op, value = param.partition('=')
        if not eq_op:
            msg = 'Malformed parameter(%s). Use the key=value format.' % param
            raise ValueError(msg)
        return key, value

    def get_parser(self, prog_name):
        parser = super(CliAlarmList, self).get_parser(prog_name)
        exclusive_group = parser.add_mutually_exclusive_group()
        exclusive_group.add_argument("--query",
                                     help="Rich query supported by aodh, "
                                          "e.g. project_id!=my-id "
                                          "user_id=foo or user_id=bar")
        exclusive_group.add_argument('--filter', dest='filter',
                                     metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
                                     type=self.split_filter_param,
                                     action='append',
                                     help='Filter parameters to apply on'
                                          ' returned alarms.')
        return parser

    def take_action(self, parsed_args):
        if parsed_args.query:
            query = jsonutils.dumps(
                utils.search_query_builder(parsed_args.query))
        else:
            query = None
        filters = dict(parsed_args.filter) if parsed_args.filter else None
        alarms = utils.get_client(self).alarm.list(query=query,
                                                   filters=filters)
        return utils.list2cols(ALARM_LIST_COLS, alarms)


def _format_alarm(alarm):
    if alarm.get('composite_rule'):
        composite_rule = jsonutils.dumps(alarm['composite_rule'], indent=2)
        alarm['composite_rule'] = composite_rule
        return alarm
    for alarm_type in ALARM_TYPES:
        if alarm.get('%s_rule' % alarm_type):
            alarm.update(alarm.pop('%s_rule' % alarm_type))
    if alarm["time_constraints"]:
        alarm["time_constraints"] = jsonutils.dumps(alarm["time_constraints"],
                                                    sort_keys=True,
                                                    indent=2)
    return alarm


def _find_alarm_by_name(client, name, return_id=False):
    # then try to get entity as name
    query = jsonutils.dumps({"=": {"name": name}})
    alarms = client.list(query)
    if len(alarms) > 1:
        msg = (_("Multiple alarms matches found for '%s', "
                 "use an ID to be more specific.") % name)
        raise exceptions.NoUniqueMatch(msg)
    elif not alarms:
        msg = (_("Alarm %s not found") % name)
        raise exceptions.NotFound(404, msg)
    else:
        if return_id:
            return alarms[0]['alarm_id']
        return alarms[0]


def _check_name_and_id(parsed_args, action):
    if parsed_args.id and parsed_args.alarm_name:
        raise exceptions.CommandError(
            "You should provide only one of "
            "alarm ID and alarm name(--alarm-name) "
            "to %s an alarm." % action)
    if not parsed_args.id and not parsed_args.alarm_name:
        msg = (_("You need to specify one of "
                 "alarm ID and alarm name(--alarm-name) "
                 "to %s an alarm.") % action)
        raise exceptions.CommandError(msg)


def _add_name_and_id(parser):
    parser.add_argument("id", nargs='?',
                        metavar='<ALARM ID>',
                        help="ID of an alarm.")
    parser.add_argument("--alarm-name", dest='alarm_name',
                        metavar='<ALARM NAME>',
                        help="Name of an alarm.")
    return parser


class CliAlarmShow(show.ShowOne):
    """Show an alarm"""

    def get_parser(self, prog_name):
        parser = super(CliAlarmShow, self).get_parser(prog_name)
        return _add_name_and_id(parser)

    def take_action(self, parsed_args):
        _check_name_and_id(parsed_args, 'query')
        if parsed_args.id:
            alarm = utils.get_client(self).alarm.get(alarm_id=parsed_args.id)
        else:
            alarm = _find_alarm_by_name(utils.get_client(self).alarm,
                                        parsed_args.alarm_name)
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
                            help=('URL to invoke when state transitions to '
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
            type=self.validate_time_constraint,
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
            '--query', metavar='<QUERY>', dest='query',
            help="For alarms of type threshold or event: "
                 "key[op]data_type::value; list. data_type is optional, "
                 "but if supplied must be string, integer, float, or boolean. "
                 'For alarms of '
                 'type gnocchi_aggregation_by_resources_threshold: '
                 'need to specify a complex query json string, like:'
                 ' {"and": [{"=": {"ended_at": null}}, ...]}.')
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
            '-m', '--meter-name', metavar='<METER NAME>',
            dest='meter_name', help='Meter to evaluate against')

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

    def validate_time_constraint(self, values_to_convert):
        """Converts 'a=1;b=2' to {a:1,b:2}."""

        try:
            return dict((item.strip(" \"'")
                         for item in kv.split("=", 1))
                        for kv in values_to_convert.split(";"))
        except ValueError:
            msg = ('must be a list of '
                   'key1=value1;key2=value2;... not %s'
                   % values_to_convert)
            raise argparse.ArgumentTypeError(msg)

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
                              '--resource-type')
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
        if parsed_args.type in ('threshold', 'event') and parsed_args.query:
            parsed_args.query = utils.cli_to_array(parsed_args.query)
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
        alarm = utils.get_client(self).alarm.create(
            alarm=self._alarm_from_args(parsed_args))
        return self.dict2columns(_format_alarm(alarm))


class CliAlarmUpdate(CliAlarmCreate):
    """Update an alarm"""

    create = False

    def get_parser(self, prog_name):
        parser = super(CliAlarmUpdate, self).get_parser(prog_name)
        return _add_name_and_id(parser)

    def take_action(self, parsed_args):
        _check_name_and_id(parsed_args, 'update')
        attributes = self._alarm_from_args(parsed_args)
        if parsed_args.id:
            updated_alarm = utils.get_client(self).alarm.update(
                alarm_id=parsed_args.id, alarm_update=attributes)
        else:
            alarm_id = _find_alarm_by_name(utils.get_client(self).alarm,
                                           parsed_args.alarm_name,
                                           return_id=True)
            updated_alarm = utils.get_client(self).alarm.update(
                alarm_id=alarm_id, alarm_update=attributes)
        return self.dict2columns(_format_alarm(updated_alarm))


class CliAlarmDelete(command.Command):
    """Delete an alarm"""

    def get_parser(self, prog_name):
        parser = super(CliAlarmDelete, self).get_parser(prog_name)
        return _add_name_and_id(parser)

    def take_action(self, parsed_args):
        _check_name_and_id(parsed_args, 'delete')
        if parsed_args.id:
            utils.get_client(self).alarm.delete(parsed_args.id)
        else:
            alarm_id = _find_alarm_by_name(utils.get_client(self).alarm,
                                           parsed_args.alarm_name,
                                           return_id=True)
            utils.get_client(self).alarm.delete(alarm_id)
