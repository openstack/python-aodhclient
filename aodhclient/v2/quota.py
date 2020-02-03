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
from oslo_serialization import jsonutils

from aodhclient.v2 import base


class QuotasManager(base.Manager):
    base_url = "v2/quotas"

    def list(self, project=None):
        url = self.base_url
        if project:
            url = "%s?project_id=%s" % (url, project)

        return self._get(url).json()

    def create(self, project, resource_quotas):
        body = {
            "project_id": project,
            "quotas": []
        }
        for q in resource_quotas:
            body['quotas'].append(
                {"resource": q['resource'], 'limit': q['limit']}
            )

        return self._post(
            self.base_url, headers={'Content-Type': "application/json"},
            data=jsonutils.dumps(body)
        ).json()
