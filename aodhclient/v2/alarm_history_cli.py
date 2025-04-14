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
from cliff import lister
from oslo_serialization import jsonutils

from aodhclient import utils


class CliAlarmHistorySearch(lister.Lister):
    """Show history for all alarms based on query"""

    COLS = ('alarm_id', 'timestamp', 'type', 'detail')

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("--query",
                            help="Rich query supported by aodh, "
                                 "e.g. project_id!=my-id "
                                 "user_id=foo or user_id=bar"),
        return parser

    def take_action(self, parsed_args):
        query = None
        if parsed_args.query:
            query = jsonutils.dumps(
                utils.search_query_builder(parsed_args.query))
        history = utils.get_client(self).alarm_history.search(
            query=query)
        return utils.list2cols(self.COLS, history)


class CliAlarmHistoryShow(lister.Lister):
    """Show history for an alarm"""

    COLS = ('timestamp', 'type', 'detail', 'event_id')

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("alarm_id", metavar="<alarm-id>",
                            help="ID of an alarm")
        parser.add_argument("--limit", type=int, metavar="<LIMIT>",
                            help="Number of resources to return "
                                 "(Default is server default)")
        parser.add_argument("--marker", metavar="<MARKER>",
                            help="Last item of the previous listing. "
                                 "Return the next results after this value,"
                                 "the supported marker is event_id.")
        parser.add_argument("--sort", action="append",
                            metavar="<SORT_KEY:SORT_DIR>",
                            help="Sort of resource attribute. "
                                 "e.g. timestamp:desc")
        return parser

    def take_action(self, parsed_args):
        history = utils.get_client(self).alarm_history.get(
            alarm_id=parsed_args.alarm_id, sorts=parsed_args.sort,
            limit=parsed_args.limit, marker=parsed_args.marker)
        return utils.list2cols(self.COLS, history)
