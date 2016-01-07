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


class AlarmHistoryManager(base.Manager):

    url = "v2/alarms/%s/history"

    def get(self, alarm_id):
        """Get history of an alarm

        :param alarm_id: ID of the alarm
        :type alarm_id: str
        """
        return self._get(self.url % alarm_id).json()

    def search(self, query=None):
        """List of history matching corresponding query

        :param query: The query dictionary
        :type query: dict
        """
        query = {'filter': query} if query else {}
        url = "v2/query/alarms/history"
        return self._post(url, headers={'Content-Type': "application/json"},
                          data=jsonutils.dumps(query)).json()
