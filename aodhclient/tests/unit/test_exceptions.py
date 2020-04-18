# Copyright 2016 Hewlett Packard Enterprise Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import mock

from oslotest import base

from aodhclient import exceptions


class AodhclientExceptionsTest(base.BaseTestCase):
    def test_string_format_base_exception(self):
        # ensure http_status has initial value N/A
        self.assertEqual('Unknown Error (HTTP N/A)',
                         '%s' % exceptions.ClientException())

    def test_no_match_exception_from_response(self):
        resp = mock.MagicMock(status_code=520)
        resp.headers = {
            'Content-Type': 'text/plain',
            'x-openstack-request-id': 'fake-request-id'
        }
        resp.text = 'Of course I still love you'
        e = exceptions.from_response(resp, 'http://no.where:2333/v2/alarms')
        self.assertIsInstance(e, exceptions.ClientException)
        self.assertEqual('Of course I still love you (HTTP 520) '
                         '(Request-ID: fake-request-id)', '%s' % e)
