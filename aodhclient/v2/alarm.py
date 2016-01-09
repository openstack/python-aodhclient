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


class AlarmManager(base.Manager):

    url = "v2/alarms"

    def list(self, alarm_type):
        """List alarms"""
        return self._get(self.url + '?q.field=type&q.op=eq' +
                         '&q.value=' + alarm_type).json()

    def get(self, alarm_id):
        """Get an alarm

        :param alarm_id: ID of the alarm
        :type alarm_id: str
        """
        return self._get(self.url + '/' + alarm_id).json()

    def create(self, alarm):
        """Create an alarm

        :param alarm: the alarm
        :type alarm: dict
        """
        return self._post(
            self.url, headers={'Content-Type': "application/json"},
            data=jsonutils.dumps(alarm)).json()

    def update(self, alarm_id, alarm_update):
        """Update an alarm

        :param alarm_id: ID of the alarm
        :type alarm_id: str
        :param attributes: Attributes of the alarm
        :type attributes: dict
        """
        alarm = self._get(self.url + '/' + alarm_id).json()
        if alarm_update.get('threshold_rule'):
            alarm['threshold_rule'].update(alarm_update.get('threshold_rule'))
            alarm_update.pop('threshold_rule')
        alarm.update(alarm_update)
        return self._put(
            self.url + '/' + alarm_id,
            headers={'Content-Type': "application/json"},
            data=jsonutils.dumps(alarm)).json()

    def delete(self, alarm_id):
        """Delete an alarm

        :param alarm_id: ID of the alarm
        :type alarm_id: str
        """
        self._delete(self.url + '/' + alarm_id)

    def search(self, query=None):
        """List alarms

        :param query: The query dictionary
        :type query: dict
        """
        query = {'filter': query} if query else {}
        url = "v2/query/alarms"
        return self._post(url, headers={'Content-Type': "application/json"},
                          data=jsonutils.dumps(query)).json()
