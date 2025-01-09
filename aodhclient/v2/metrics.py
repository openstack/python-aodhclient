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

from aodhclient.v2 import base


class MetricsManager(base.Manager):

    url = "v2/metrics"

    def get(self, all_projects=False):
        """Get metrics"""
        if all_projects:
            return self._get(self.url + "?all_projects=true").json()
        else:
            return self._get(self.url).json()
