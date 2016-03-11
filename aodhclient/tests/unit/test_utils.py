# -*- encoding: utf-8 -*-
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

from oslotest import base

from aodhclient import utils


class SearchQueryBuilderTest(base.BaseTestCase):
    def _do_test(self, expr, expected):
        req = utils.search_query_builder(expr)
        self.assertEqual(expected, req)

    def test_search_query_builder(self):
        self._do_test('foo=bar', {"=": {"foo": "bar"}})
        self._do_test('foo!=1', {"!=": {"foo": 1.0}})
        self._do_test('foo=True', {"=": {"foo": True}})
        self._do_test('foo=null', {"=": {"foo": None}})
        self._do_test('foo="null"', {"=": {"foo": "null"}})

        self._do_test('not (foo="quote" or foo="what!" '
                      'or bar="who?")',
                      {"not": {"or": [
                          {"=": {"bar": "who?"}},
                          {"=": {"foo": "what!"}},
                          {"=": {"foo": "quote"}},
                      ]}})

        self._do_test('(foo="quote" or not foo="what!" '
                      'or bar="who?") and cat="meme"',
                      {"and": [
                          {"=": {"cat": "meme"}},
                          {"or": [
                              {"=": {"bar": "who?"}},
                              {"not": {"=": {"foo": "what!"}}},
                              {"=": {"foo": "quote"}},
                          ]}
                      ]})

        self._do_test('foo="quote" or foo="what!" '
                      'or bar="who?" and cat="meme"',
                      {"or": [
                          {"and": [
                              {"=": {"cat": "meme"}},
                              {"=": {"bar": "who?"}},
                          ]},
                          {"=": {"foo": "what!"}},
                          {"=": {"foo": "quote"}},
                      ]})

        self._do_test('foo="quote" and foo="what!" '
                      'or bar="who?" or cat="meme"',
                      {'or': [
                          {'=': {'cat': 'meme'}},
                          {'=': {'bar': 'who?'}},
                          {'and': [
                              {'=': {'foo': 'what!'}},
                              {'=': {'foo': 'quote'}}
                          ]}
                      ]})


class CliQueryToArray(base.BaseTestCase):
    def test_cli_query_to_arrary(self):
        cli_query = "this<=34;that=string::foo"
        ret_array = utils.cli_to_array(cli_query)
        expected_query = [
            {"field": "this", "type": "", "value": "34", "op": "le"},
            {"field": "that", "type": "string", "value": "foo", "op": "eq"}]
        self.assertEqual(expected_query, ret_array)
