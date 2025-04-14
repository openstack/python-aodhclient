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

from aodhclient import utils
from aodhclient.v2 import alarm_cli
from aodhclient.v2 import base


class AlarmManager(base.Manager):

    url = "v2/alarms"

    @staticmethod
    def _filtersdict_to_url(filters):
        urls = []
        for k, v in sorted(filters.items()):
            url = "q.field={}&q.op=eq&q.value={}".format(k, v)
            urls.append(url)
        return '&'.join(urls)

    def list(self, filters=None, limit=None,
             marker=None, sorts=None):
        """List alarms.

        :param filters: A dict includes filters parameters, for example,
                        {'type': 'gnocchi_resources_threshold',
                         'severity': 'low'} represent filters to query alarms
                        with type='gnocchi_resources_threshold' and
                        severity='low'.
        :type filters: dict
        :param limit: maximum number of resources to return
        :type limit: int
        :param marker: the last item of the previous page; we return the next
                       results after this value.
        :type marker: str
        :param sorts: list of resource attributes to order by.
        :type sorts: list of str
        """
        pagination = utils.get_pagination_options(limit, marker, sorts)
        filter_string = (self._filtersdict_to_url(filters) if
                         filters else "")
        url = self.url
        options = []
        if filter_string:
            options.append(filter_string)
        if pagination:
            options.append(pagination)
        if options:
            url += "?" + "&".join(options)
        return self._get(url).json()

    def query(self, query=None):
        """Query alarms.

        :param query: A json format complex query expression, like this:
                      '{"=":{"type":"gnocchi_resources_threshold"}}', this
                      expression is used to query all the
                      gnocchi_resources_threshold type alarms.
        :type query: json
        """
        query = {'filter': query}
        url = "v2/query/alarms"
        return self._post(url,
                          headers={'Content-Type': "application/json"},
                          data=jsonutils.dumps(query)).json()

    def get(self, alarm_id):
        """Get an alarm

        :param alarm_id: ID of the alarm
        :type alarm_id: str
        """
        return self._get(self.url + '/' + alarm_id).json()

    @staticmethod
    def _clean_rules(alarm_type, alarm):
        for rule in alarm_cli.ALARM_TYPES:
            if rule != alarm_type:
                alarm.pop('%s_rule' % rule, None)

    def create(self, alarm):
        """Create an alarm

        :param alarm: the alarm
        :type alarm: dict
        """
        self._clean_rules(alarm['type'], alarm)
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
        if 'type' not in alarm_update:
            self._clean_rules(alarm['type'], alarm_update)
        else:
            self._clean_rules(alarm_update['type'], alarm_update)

        if 'prometheus_rule' in alarm_update:
            rule = alarm_update.get('prometheus_rule')
            alarm['prometheus_rule'].update(rule)
            alarm_update.pop('prometheus_rule')
        elif 'threshold_rule' in alarm_update:
            alarm['threshold_rule'].update(alarm_update.get('threshold_rule'))
            alarm_update.pop('threshold_rule')
        elif 'event_rule' in alarm_update:
            if ('type' in alarm_update and
                    alarm_update['type'] != alarm['type']):
                alarm.pop('%s_rule' % alarm['type'], None)
                alarm['event_rule'] = alarm_update['event_rule']
            else:
                alarm['event_rule'].update(alarm_update.get('event_rule'))
            alarm_update.pop('event_rule')
        elif 'gnocchi_resources_threshold_rule' in alarm_update:
            if ('type' in alarm_update and
                    alarm_update['type'] != alarm['type']):
                alarm.pop('%s_rule' % alarm['type'], None)
                alarm['gnocchi_resources_threshold_rule'] = alarm_update[
                    'gnocchi_resources_threshold_rule']
            else:
                alarm['gnocchi_resources_threshold_rule'].update(
                    alarm_update.get('gnocchi_resources_threshold_rule'))
            alarm_update.pop('gnocchi_resources_threshold_rule')
        elif 'gnocchi_aggregation_by_metrics_threshold_rule' in alarm_update:
            if ('type' in alarm_update and
                    alarm_update['type'] != alarm['type']):
                alarm.pop('%s_rule' % alarm['type'], None)
                alarm['gnocchi_aggregation_by_metrics_threshold_rule'] = \
                    alarm_update[
                        'gnocchi_aggregation_by_metrics_threshold_rule']
            else:
                alarm['gnocchi_aggregation_by_metrics_threshold_rule'].update(
                    alarm_update.get(
                        'gnocchi_aggregation_by_metrics_threshold_rule'))
            alarm_update.pop('gnocchi_aggregation_by_metrics_threshold_rule')
        elif 'gnocchi_aggregation_by_resources_threshold_rule' in alarm_update:
            if ('type' in alarm_update and
                    alarm_update['type'] != alarm['type']):
                alarm.pop('%s_rule' % alarm['type'], None)
                alarm['gnocchi_aggregation_by_resources_threshold_rule'] = \
                    alarm_update[
                        'gnocchi_aggregation_by_resources_threshold_rule']
            else:
                alarm['gnocchi_aggregation_by_resources_threshold_rule'].\
                    update(alarm_update.get(
                        'gnocchi_aggregation_by_resources_threshold_rule'))
            alarm_update.pop(
                'gnocchi_aggregation_by_resources_threshold_rule')
        elif 'composite_rule' in alarm_update:
            if ('type' in alarm_update and
                    alarm_update['type'] != alarm['type']):
                alarm.pop('%s_rule' % alarm['type'], None)
            if alarm_update['composite_rule'] is not None:
                alarm['composite_rule'] = alarm_update[
                    'composite_rule']
            alarm_update.pop('composite_rule')
        elif 'loadbalancer_member_health_rule' in alarm_update:
            if ('type' in alarm_update and
                    alarm_update['type'] != alarm['type']):
                alarm.pop('%s_rule' % alarm['type'], None)
            if alarm_update['loadbalancer_member_health_rule'] is not None:
                alarm['loadbalancer_member_health_rule'] = alarm_update[
                    'loadbalancer_member_health_rule']
            alarm_update.pop('loadbalancer_member_health_rule')

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

    def get_state(self, alarm_id):
        """Get the state of an alarm

        :param alarm_id: ID of the alarm
        :type alarm_id: str
        """
        return self._get(self.url + '/' + alarm_id + '/state').json()

    def set_state(self, alarm_id, state):
        """Set the state of an alarm

        :param alarm_id: ID of the alarm
        :type alarm_id: str
        :param state: the state to be updated to the alarm
        :type state: str
        """
        return self._put(self.url + '/' + alarm_id + '/state',
                         headers={'Content-Type': "application/json"},
                         data='"%s"' % state
                         ).json()
