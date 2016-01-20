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
from oslo_utils import strutils

from aodhclient import utils


ALARM_STATES = ['ok', 'alarm', 'insufficient data']
ALARM_SEVERITY = ['low', 'moderate', 'critical']
ALARM_OPERATORS = ['lt', 'le', 'eq', 'ne', 'ge', 'gt']
STATISTICS = ['max', 'min', 'avg', 'sum', 'count']


class CliAlarmList(lister.Lister):
    """List alarms"""

    COLS = ('alarm_id', 'name', 'state', 'severity', 'enabled',
            'repeat_actions', 'threshold_rule', 'time_constraints')

    def take_action(self, parsed_args):
        alarms = self.app.client.alarm.list()
        return utils.list2cols(self.COLS, alarms)


class CliAlarmSearch(CliAlarmList):
    """Search alarms with specified query rules"""

    def get_parser(self, prog_name):
        parser = super(CliAlarmSearch, self).get_parser(prog_name)
        parser.add_argument("--query", help="Query"),
        return parser

    def take_action(self, parsed_args):
        alarms = self.app.client.alarm.search(query=parsed_args.query)
        return utils.list2cols(self.COLS, alarms)


def _format_alarm(alarm):
    alarm.update(alarm.pop('threshold_rule'))
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
                            help='State of the alarm, one of: '
                            + str(ALARM_STATES))
        parser.add_argument('--severity', metavar='<SEVERITY>',
                            help='Severity of the alarm, one of: '
                            + str(ALARM_SEVERITY))
        parser.add_argument('--enabled', type=strutils.bool_from_string,
                            metavar='{True|False}',
                            help=('True if alarm evaluation/actioning is '
                                  'enabled'))
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
        parser.add_argument(
            '-m', '--meter-name', metavar='<METRIC>', required=self.create,
            dest='meter_name', help='Metric to evaluate against')
        parser.add_argument(
            '--period', type=int, metavar='<PERIOD>', dest='period',
            help='Length of each period (seconds) to evaluate over.')
        parser.add_argument(
            '--evaluation-periods', type=int, metavar='<EVAL_PERIODS>',
            dest='evaluation_periods',
            help='Number of periods to evaluate over')
        parser.add_argument(
            '--statistic', metavar='<STATISTIC>', dest='statistic',
            help='Statistic to evaluate, one of: ' + str(STATISTICS))
        parser.add_argument(
            '--comparison-operator', metavar='<OPERATOR>',
            dest='comparison_operator',
            help='Operator to compare with, one of: ' + str(ALARM_OPERATORS))
        parser.add_argument(
            '--threshold', type=float, metavar='<THRESHOLD>',
            required=self.create, dest='threshold',
            help='Threshold to evaluate against.')
        parser.add_argument(
            '-q', '--query', metavar='<QUERY>', dest='query',
            help='key[op]data_type::value; list. data_type is optional, '
                 'but if supplied must be string, integer, float, or boolean.')

        return parser

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
        if self.create:
            alarm['type'] = 'threshold'
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
