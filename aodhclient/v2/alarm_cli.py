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
from oslo_utils import uuidutils

from aodhclient import exceptions
from aodhclient.i18n import _
from aodhclient import utils

ALARM_TYPES = ['event', 'composite',
               'gnocchi_resources_threshold',
               'gnocchi_aggregation_by_metrics_threshold',
               'gnocchi_aggregation_by_resources_threshold']
ALARM_STATES = ['ok', 'alarm', 'insufficient data']
ALARM_SEVERITY = ['low', 'moderate', 'critical']
ALARM_OPERATORS = ['lt', 'le', 'eq', 'ne', 'ge', 'gt']
ALARM_OP_MAP = dict(zip(ALARM_OPERATORS, ('<', '<=', '=', '!=', '>=', '>')))

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
        parser.add_argument("--limit", type=int, metavar="<LIMIT>",
                            help="Number of resources to return "
                                 "(Default is server default)")
        parser.add_argument("--marker", metavar="<MARKER>",
                            help="Last item of the previous listing. "
                                 "Return the next results after this value,"
                                 "the supported marker is alarm_id.")
        parser.add_argument("--sort", action="append",
                            metavar="<SORT_KEY:SORT_DIR>",
                            help="Sort of resource attribute, "
                                 "e.g. name:asc")
        return parser

    def take_action(self, parsed_args):
        if parsed_args.query:
            if any([parsed_args.limit, parsed_args.sort, parsed_args.marker]):
                raise exceptions.CommandError(
                    "Query and pagination options are mutually "
                    "exclusive.")
            query = jsonutils.dumps(
                utils.search_query_builder(parsed_args.query))
            alarms = utils.get_client(self).alarm.query(query=query)
        else:
            filters = dict(parsed_args.filter) if parsed_args.filter else None
            alarms = utils.get_client(self).alarm.list(
                filters=filters, sorts=parsed_args.sort,
                limit=parsed_args.limit, marker=parsed_args.marker)
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
    # only works for event alarm
    if isinstance(alarm.get('query'), list):
        query_rows = []
        for q in alarm['query']:
            op = ALARM_OP_MAP.get(q['op'], q['op'])
            query_rows.append('%s %s %s' % (q['field'], op, q['value']))
        alarm['query'] = ' AND\n'.join(query_rows)
    return alarm


def _find_alarm_by_name(client, name):
    # then try to get entity as name
    query = jsonutils.dumps({"=": {"name": name}})
    alarms = client.alarm.query(query)
    if len(alarms) > 1:
        msg = (_("Multiple alarms matches found for '%s', "
                 "use an ID to be more specific.") % name)
        raise exceptions.NoUniqueMatch(msg)
    elif not alarms:
        msg = (_("Alarm %s not found") % name)
        raise exceptions.NotFound(msg)
    else:
        return alarms[0]


def _find_alarm_id_by_name(client, name):
    alarm = _find_alarm_by_name(client, name)
    return alarm['alarm_id']


def _check_name_and_id_coexist(parsed_args, action):
    if parsed_args.id and parsed_args.name:
        raise exceptions.CommandError(
            "You should provide only one of "
            "alarm ID and alarm name(--name) "
            "to %s an alarm." % action)


def _check_name_and_id_exist(parsed_args, action):
    if not parsed_args.id and not parsed_args.name:
        msg = (_("You need to specify one of "
                 "alarm ID and alarm name(--name) "
                 "to %s an alarm.") % action)
        raise exceptions.CommandError(msg)


def _check_name_and_id(parsed_args, action):
    _check_name_and_id_coexist(parsed_args, action)
    _check_name_and_id_exist(parsed_args, action)


def _add_name_to_parser(parser, required=False):
    parser.add_argument('--name', metavar='<NAME>',
                        required=required,
                        help='Name of the alarm')
    return parser


def _add_id_to_parser(parser):
    parser.add_argument("id", nargs='?',
                        metavar='<ALARM ID or NAME>',
                        help="ID or name of an alarm.")
    return parser


class CliAlarmShow(show.ShowOne):
    """Show an alarm"""

    def get_parser(self, prog_name):
        return _add_name_to_parser(
            _add_id_to_parser(
                super(CliAlarmShow, self).get_parser(prog_name)))

    def take_action(self, parsed_args):
        _check_name_and_id(parsed_args, 'query')
        c = utils.get_client(self)
        if parsed_args.name:
            alarm = _find_alarm_by_name(c, parsed_args.name)
        else:
            if uuidutils.is_uuid_like(parsed_args.id):
                try:
                    alarm = c.alarm.get(alarm_id=parsed_args.id)
                except exceptions.NotFound:
                    # Maybe it's a name
                    alarm = _find_alarm_by_name(c, parsed_args.id)
            else:
                alarm = _find_alarm_by_name(c, parsed_args.id)

        return self.dict2columns(_format_alarm(alarm))


class CliAlarmCreate(show.ShowOne):
    """Create an alarm"""

    create = True

    def get_parser(self, prog_name):
        parser = _add_name_to_parser(
            super(CliAlarmCreate, self).get_parser(prog_name),
            required=self.create)

        parser.add_argument('-t', '--type', metavar='<TYPE>',
                            required=self.create,
                            choices=ALARM_TYPES,
                            help='Type of alarm, should be one of: '
                                 '%s.' % ', '.join(ALARM_TYPES))
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
            help="For alarms of type event: "
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
        gnocchi_common_group.add_argument(
            '--metric', '--metrics', metavar='<METRIC>', action='append',
            dest='metrics', help='The metric id or name '
            'depending of the alarm type')

        gnocchi_resource_threshold_group = parser.add_argument_group(
            'gnocchi resource threshold alarm')
        gnocchi_resource_threshold_group.add_argument(
            '--resource-type', metavar='<RESOURCE_TYPE>',
            dest='resource_type', help='The type of resource.')
        gnocchi_resource_threshold_group.add_argument(
            '--resource-id', metavar='<RESOURCE_ID>',
            dest='resource_id', help='The id of a resource.')

        composite_group = parser.add_argument_group('composite alarm')
        composite_group.add_argument(
            '--composite-rule', metavar='<COMPOSITE_RULE>',
            dest='composite_rule',
            type=jsonutils.loads,
            help='Composite threshold rule with JSON format, the form can '
                 'be a nested dict which combine gnocchi rules by '
                 '"and", "or". For example, the form is like: '
                 '{"or":[RULE1, RULE2, {"and": [RULE3, RULE4]}]}.'
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
        if (parsed_args.type == 'gnocchi_resources_threshold' and
                not (parsed_args.metrics and parsed_args.threshold is not None
                     and parsed_args.resource_id and parsed_args.resource_type
                     and parsed_args.aggregation_method)):
            self.parser.error('gnocchi_resources_threshold requires --metric, '
                              '--threshold, --resource-id, --resource-type '
                              'and --aggregation-method')
        elif (parsed_args.type == 'gnocchi_aggregation_by_metrics_threshold'
              and not (parsed_args.metrics
                       and parsed_args.threshold is not None
                       and parsed_args.aggregation_method)):
            self.parser.error('gnocchi_aggregation_by_metrics_threshold '
                              'requires --metric, --threshold and '
                              '--aggregation-method')
        elif (parsed_args.type == 'gnocchi_aggregation_by_resources_threshold'
              and not (parsed_args.metrics
                       and parsed_args.threshold is not None
                       and parsed_args.query and parsed_args.resource_type and
                       parsed_args.aggregation_method)):
            self.parser.error('gnocchi_aggregation_by_resources_threshold '
                              'requires --metric, --threshold, '
                              '--aggregation-method, --query and '
                              '--resource-type')
        elif (parsed_args.type == 'composite' and
              not parsed_args.composite_rule):
            self.parser.error('Composite alarm requires'
                              ' --composite-rule parameter')

    def _alarm_from_args(self, parsed_args):
        alarm = utils.dict_from_parsed_args(
            parsed_args, ['name', 'project_id', 'user_id', 'description',
                          'state', 'severity', 'enabled', 'alarm_actions',
                          'ok_actions', 'insufficient_data_actions',
                          'time_constraints', 'repeat_actions'])
        if parsed_args.type == 'event' and parsed_args.query:
            parsed_args.query = utils.cli_to_array(parsed_args.query)
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
        return _add_id_to_parser(
            super(CliAlarmUpdate, self).get_parser(prog_name))

    def take_action(self, parsed_args):
        attributes = self._alarm_from_args(parsed_args)
        _check_name_and_id_exist(parsed_args, 'update')
        c = utils.get_client(self)

        if uuidutils.is_uuid_like(parsed_args.id):
            try:
                alarm = c.alarm.update(alarm_id=parsed_args.id,
                                       alarm_update=attributes)
            except exceptions.NotFound:
                # Maybe it was not an ID but a name, damn
                _id = _find_alarm_id_by_name(c, parsed_args.id)
            else:
                return self.dict2columns(_format_alarm(alarm))
        elif parsed_args.id:
            _id = _find_alarm_id_by_name(c, parsed_args.id)
        else:
            _id = _find_alarm_id_by_name(c, parsed_args.name)

        alarm = c.alarm.update(alarm_id=_id, alarm_update=attributes)
        return self.dict2columns(_format_alarm(alarm))


class CliAlarmDelete(command.Command):
    """Delete an alarm"""

    def get_parser(self, prog_name):
        return _add_name_to_parser(
            _add_id_to_parser(
                super(CliAlarmDelete, self).get_parser(prog_name)))

    def take_action(self, parsed_args):
        _check_name_and_id(parsed_args, 'delete')
        c = utils.get_client(self)

        if parsed_args.name:
            _id = _find_alarm_id_by_name(c, parsed_args.name)
        elif uuidutils.is_uuid_like(parsed_args.id):
            try:
                return c.alarm.delete(parsed_args.id)
            except exceptions.NotFound:
                # Maybe it was not an ID after all
                _id = _find_alarm_id_by_name(c, parsed_args.id)
        else:
            _id = _find_alarm_id_by_name(c, parsed_args.id)

        c.alarm.delete(_id)


class CliAlarmStateGet(show.ShowOne):
    """Get state of an alarm"""

    def get_parser(self, prog_name):
        return _add_name_to_parser(
            _add_id_to_parser(
                super(CliAlarmStateGet, self).get_parser(prog_name)))

    def take_action(self, parsed_args):
        _check_name_and_id(parsed_args, 'get state of')
        c = utils.get_client(self)

        if parsed_args.name:
            _id = _find_alarm_id_by_name(c, parsed_args.name)
        elif uuidutils.is_uuid_like(parsed_args.id):
            try:
                state = c.alarm.get_state(parsed_args.id)
            except exceptions.NotFound:
                # Maybe it was not an ID after all
                _id = _find_alarm_id_by_name(c, parsed_args.id)
            else:
                return self.dict2columns({'state': state})
        else:
            _id = _find_alarm_id_by_name(c, parsed_args.id)

        state = c.alarm.get_state(_id)
        return self.dict2columns({'state': state})


class CliAlarmStateSet(show.ShowOne):
    """Set state of an alarm"""

    def get_parser(self, prog_name):
        parser = _add_name_to_parser(
            _add_id_to_parser(
                super(CliAlarmStateSet, self).get_parser(prog_name)))
        parser.add_argument('--state', metavar='<STATE>',
                            required=True,
                            choices=ALARM_STATES,
                            help='State of the alarm, one of: '
                            + str(ALARM_STATES))
        return parser

    def take_action(self, parsed_args):
        _check_name_and_id(parsed_args, 'set state of')
        c = utils.get_client(self)

        if parsed_args.name:
            _id = _find_alarm_id_by_name(c, parsed_args.name)
        elif uuidutils.is_uuid_like(parsed_args.id):
            try:
                state = c.alarm.set_state(parsed_args.id, parsed_args.state)
            except exceptions.NotFound:
                # Maybe it was not an ID after all
                _id = _find_alarm_id_by_name(c, parsed_args.id)
            else:
                return self.dict2columns({'state': state})
        else:
            _id = _find_alarm_id_by_name(c, parsed_args.id)

        state = c.alarm.set_state(_id, parsed_args.state)
        return self.dict2columns({'state': state})
