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
from cliff import show

from aodhclient import exceptions
from aodhclient import utils


class QuotaShow(show.ShowOne):
    """Show quota for a project"""

    def get_parser(self, prog_name):
        parser = super(QuotaShow, self).get_parser(prog_name)
        parser.add_argument(
            "--project",
            help="Project ID. If not specified, get quota for the current "
                 "project."
        )
        return parser

    def take_action(self, parsed_args):
        c = utils.get_client(self)
        quota = c.quota.list(project=parsed_args.project)

        ret = {}
        for q in quota['quotas']:
            ret[q['resource']] = q['limit']

        return self.dict2columns(ret)


class QuotaSet(show.ShowOne):
    def get_parser(self, prog_name):
        parser = super(QuotaSet, self).get_parser(prog_name)
        parser.add_argument(
            "project",
            help="Project ID."
        )
        parser.add_argument(
            "--alarm", type=int,
            help="New value for the alarm quota. Value -1 means unlimited."
        )
        return parser

    def take_action(self, parsed_args):
        resource_quotas = []
        if parsed_args.alarm is not None:
            if parsed_args.alarm < -1:
                raise exceptions.CommandError(
                    'Quota limit cannot be less than -1.')
            resource_quotas.append(
                {'resource': 'alarms', 'limit': parsed_args.alarm})

        c = utils.get_client(self)
        quota = c.quota.create(parsed_args.project, resource_quotas)

        ret = {}
        for q in quota['quotas']:
            ret[q['resource']] = q['limit']

        return self.dict2columns(ret)
