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

from aodhclient import utils

METRIC_COLS = ["name", "labels", "value"]


class CliMetrics(lister.Lister):
    """Get Metrics"""

    @staticmethod
    def metrics2cols(metrics):
        cols_data = []
        if "evaluation_results" in metrics:
            for alarm in metrics["evaluation_results"]:
                for state, count in alarm["state_counters"].items():
                    # prometheus style labels
                    labels = ('alarm_id="{{{}}}", project_id="{{{}}}", '
                              'state="{{{}}}"').format(alarm['alarm_id'],
                                                       alarm['project_id'],
                                                       state)
                    cols_data.append(["evaluation_result", labels, count])
        # Extend for other types of metrics here
        return METRIC_COLS, cols_data

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        metrics = utils.get_client(self).metrics.get()
        return self.metrics2cols(metrics)
