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
import re
from six.moves.urllib import parse as urllib_parse

import pyparsing as pp

uninary_operators = ("not", )
binary_operator = (u">=", u"<=", u"!=", u">", u"<", u"=", u"==", u"eq", u"ne",
                   u"lt", u"gt", u"ge", u"le")
multiple_operators = (u"and", u"or")

operator = pp.Regex(u"|".join(binary_operator))
null = pp.Regex("None|none|null").setParseAction(pp.replaceWith(None))
boolean = "False|True|false|true"
boolean = pp.Regex(boolean).setParseAction(lambda t: t[0].lower() == "true")
hex_string = lambda n: pp.Word(pp.hexnums, exact=n)
uuid = pp.Combine(hex_string(8) + ("-" + hex_string(4)) * 3 +
                  "-" + hex_string(12))
number = r"[+-]?\d+(:?\.\d*)?(:?[eE][+-]?\d+)?"
number = pp.Regex(number).setParseAction(lambda t: float(t[0]))
identifier = pp.Word(pp.alphas, pp.alphanums + "_")
quoted_string = pp.QuotedString('"') | pp.QuotedString("'")
comparison_term = pp.Forward()
in_list = pp.Group(pp.Suppress('[') +
                   pp.Optional(pp.delimitedList(comparison_term)) +
                   pp.Suppress(']'))("list")
comparison_term << (null | boolean | uuid | identifier | number |
                    quoted_string)
condition = pp.Group(comparison_term + operator + comparison_term)

expr = pp.operatorPrecedence(condition, [
    ("not", 1, pp.opAssoc.RIGHT, ),
    ("and", 2, pp.opAssoc.LEFT, ),
    ("or", 2, pp.opAssoc.LEFT, ),
])

OP_LOOKUP = {'!=': 'ne',
             '>=': 'ge',
             '<=': 'le',
             '>': 'gt',
             '<': 'lt',
             '=': 'eq'}

OP_LOOKUP_KEYS = '|'.join(sorted(OP_LOOKUP.keys(), key=len, reverse=True))
OP_SPLIT_RE = re.compile(r'(%s)' % OP_LOOKUP_KEYS)


def _parsed_query2dict(parsed_query):
    result = None
    while parsed_query:
        part = parsed_query.pop()
        if part in binary_operator:
            result = {part: {parsed_query.pop(): result}}

        elif part in multiple_operators:
            if result.get(part):
                result[part].append(
                    _parsed_query2dict(parsed_query.pop()))
            else:
                result = {part: [result]}

        elif part in uninary_operators:
            result = {part: result}
        elif isinstance(part, pp.ParseResults):
            kind = part.getName()
            if kind == "list":
                res = part.asList()
            else:
                res = _parsed_query2dict(part)
            if result is None:
                result = res
            elif isinstance(result, dict):
                list(result.values())[0].append(res)
        else:
            result = part
    return result


def search_query_builder(query):
    parsed_query = expr.parseString(query)[0]
    return _parsed_query2dict(parsed_query)


def list2cols(cols, objs):
    return cols, [tuple([o[k] for k in cols])
                  for o in objs]


def format_string_list(objs, field):
    objs[field] = ", ".join(objs[field])


def format_dict_list(objs, field):
    objs[field] = "\n".join(
        "- " + ", ".join("%s: %s" % (k, v)
                         for k, v in elem.items())
        for elem in objs[field])


def format_move_dict_to_root(obj, field):
    for attr in obj[field]:
        obj["%s/%s" % (field, attr)] = obj[field][attr]
    del obj[field]


def format_archive_policy(ap):
    format_dict_list(ap, "definition")
    format_string_list(ap, "aggregation_methods")


def dict_from_parsed_args(parsed_args, attrs):
    d = {}
    for attr in attrs:
        if attr == "metric":
            if parsed_args.metrics:
                value = parsed_args.metrics[0]
            else:
                value = None
        else:
            value = getattr(parsed_args, attr)
        if value is not None:
            d[attr] = value
    return d


def dict_to_querystring(objs):
    return "&".join(["%s=%s" % (k, v)
                     for k, v in objs.items()
                     if v is not None])


def cli_to_array(cli_query):
    """Convert CLI list of queries to the Python API format.

    This will convert the following:
        "this<=34;that=string::foo"
    to
        "[{field=this,op=le,value=34,type=''},
          {field=that,op=eq,value=foo,type=string}]"

    """

    opts = []
    queries = cli_query.split(';')
    for q in queries:
        try:
            field, q_operator, type_value = OP_SPLIT_RE.split(q, maxsplit=1)
        except ValueError:
            raise ValueError('Invalid or missing operator in query %(q)s,'
                             'the supported operators are: %(k)s' %
                             {'q': q, 'k': OP_LOOKUP.keys()})
        if not field:
            raise ValueError('Missing field in query %s' % q)
        if not type_value:
            raise ValueError('Missing value in query %s' % q)
        opt = dict(field=field, op=OP_LOOKUP[q_operator])

        if '::' not in type_value:
            opt['type'], opt['value'] = '', type_value
        else:
            opt['type'], _, opt['value'] = type_value.partition('::')

        if opt['type'] and opt['type'] not in (
                'string', 'integer', 'float', 'datetime', 'boolean'):
            err = ('Invalid value type %(type)s, the type of value'
                   'should be one of: integer, string, float, datetime,'
                   ' boolean.' % opt)
            raise ValueError(err)
        opts.append(opt)
    return opts


def get_pagination_options(limit=None, marker=None, sorts=None):
    options = []
    if limit:
        options.append("limit=%d" % limit)
    if marker:
        options.append("marker=%s" % urllib_parse.quote(marker))
    for sort in sorts or []:
        options.append("sort=%s" % urllib_parse.quote(sort))
    return "&".join(options)


def get_client(obj):
    if hasattr(obj.app, 'client_manager'):
        # NOTE(liusheng): cliff objects loaded by OSC
        return obj.app.client_manager.alarming
    else:
        # TODO(liusheng): Remove this when OSC is able
        # to install the aodh client binary itself
        return obj.app.client
