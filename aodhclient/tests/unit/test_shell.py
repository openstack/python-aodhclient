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

import io
import sys
from unittest import mock

from keystoneauth1 import exceptions
import testtools

from aodhclient import shell


class CliTest(testtools.TestCase):

    @mock.patch('sys.stderr', io.StringIO())
    def test_cli_http_error_with_details(self):
        shell.AodhShell().clean_up(
            None, None, exceptions.HttpError('foo', details='bar'))
        stderr_lines = sys.stderr.getvalue().splitlines()
        self.assertEqual(1, len(stderr_lines))
        self.assertEqual('bar', stderr_lines[0])

    @mock.patch('sys.stderr', io.StringIO())
    def test_cli_http_error_without_details(self):
        shell.AodhShell().clean_up(None, None, exceptions.HttpError('foo'))
        stderr_lines = sys.stderr.getvalue().splitlines()
        self.assertEqual(0, len(stderr_lines))
