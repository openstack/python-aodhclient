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
import time

from openstack import config as occ
from oslo_utils import uuidutils
from tempest.lib.cli import base
from tempest.lib import exceptions


class AodhClient:
    """Aodh Client for tempest-lib

    This client doesn't use any authentication system
    """

    def __init__(self):
        self.cli_dir = os.environ.get('AODH_CLIENT_EXEC_DIR')
        self.endpoint = os.environ.get('AODH_ENDPOINT')
        self.cloud = os.environ.get('OS_ADMIN_CLOUD', 'devstack-admin')
        self.user_id = uuidutils.generate_uuid()
        self.project_id = uuidutils.generate_uuid()

    def aodh(self, action, flags='', params='',
             fail_ok=False, merge_stderr=False):
        auth_args = []
        if self.cloud is None:
            auth_args.append("--os-auth-type none")
        elif self.cloud != '':
            conf = occ.OpenStackConfig()
            creds = conf.get_one(cloud=self.cloud).get_auth_args()
            auth_args.append(f"--os-auth-url {creds['auth_url']}")
            auth_args.append(f"--os-username {creds['username']}")
            auth_args.append(f"--os-password {creds['password']}")
            auth_args.append(f"--os-project-name {creds['project_name']}")
            auth_args.append(f"--os-user-domain-id {creds['user_domain_id']}")
            auth_args.append("--os-project-domain-id "
                             f"{creds['project_domain_id']}")
        endpoint_arg = "--aodh-endpoint %s" % self.endpoint

        flags = " ".join(auth_args + [endpoint_arg] + [flags])

        return base.execute("aodh", action, flags, params, fail_ok,
                            merge_stderr, self.cli_dir)


class ClientTestBase(base.ClientTestBase):
    """Base class for aodhclient tests.

    Establishes the aodhclient and retrieves the essential environment
    information.
    """

    def _get_clients(self):
        return AodhClient()

    def retry_aodh(self, retry, *args, **kwargs):
        result = ""
        while not result.strip() and retry > 0:
            result = self.aodh(*args, **kwargs)
            if not result:
                time.sleep(1)
                retry -= 1
        return result

    def aodh(self, *args, **kwargs):
        return self.clients.aodh(*args, **kwargs)

    def get_token(self):
        cloud = os.environ.get('OS_ADMIN_CLOUD', 'devstack-admin')
        if cloud is not None and cloud != "":
            conf = occ.OpenStackConfig()
            region_conf = conf.get_one(cloud=cloud)
            return region_conf.get_auth().get_token(region_conf.get_session())
        else:
            return ""

    def details_multiple(self, output_lines, with_label=False):
        """Return list of dicts with item details from cli output tables.

        If with_label is True, key '__label' is added to each items dict.
        For more about 'label' see OutputParser.tables().

        NOTE(sileht): come from tempest-lib just because cliff use
        Field instead of Property as first columun header.
        """
        items = []
        tables_ = self.parser.tables(output_lines)
        for table_ in tables_:
            if ('Field' not in table_['headers']
                    or 'Value' not in table_['headers']):
                raise exceptions.InvalidStructure()
            item = {}
            for value in table_['values']:
                item[value[0]] = value[1]
            if with_label:
                item['__label'] = table_['label']
            items.append(item)
        return items
