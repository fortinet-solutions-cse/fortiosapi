########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from yaml.reader import Reader
from yaml.scanner import Scanner
from yaml.composer import Composer
from yaml.resolver import Resolver
from yaml.parser import Parser
from yaml.constructor import SafeConstructor

from dsl_parser import holder


class HolderConstructor(SafeConstructor):

    def __init__(self, filename):
        SafeConstructor.__init__(self)
        self.filename = filename

    def construct_yaml_null(self, node):
        obj = SafeConstructor.construct_yaml_null(self, node)
        return self._holder(obj, node)

    def construct_yaml_bool(self, node):
        obj = SafeConstructor.construct_yaml_bool(self, node)
        return self._holder(obj, node)

    def construct_yaml_int(self, node):
        obj = SafeConstructor.construct_yaml_int(self, node)
        return self._holder(obj, node)

    def construct_yaml_float(self, node):
        obj = SafeConstructor.construct_yaml_float(self, node)
        return self._holder(obj, node)

    def construct_yaml_binary(self, node):
        obj = SafeConstructor.construct_yaml_binary(self, node)
        return self._holder(obj, node)

    def construct_yaml_timestamp(self, node):
        obj = SafeConstructor.construct_yaml_timestamp(self, node)
        return self._holder(obj, node)

    def construct_yaml_omap(self, node):
        obj, = SafeConstructor.construct_yaml_omap(self, node)
        return self._holder(obj, node)

    def construct_yaml_pairs(self, node):
        obj, = SafeConstructor.construct_yaml_pairs(self, node)
        return self._holder(obj, node)

    def construct_yaml_set(self, node):
        obj, = SafeConstructor.construct_yaml_set(self, node)
        return self._holder(obj, node)

    def construct_yaml_str(self, node):
        obj = SafeConstructor.construct_yaml_str(self, node)
        return self._holder(obj, node)

    def construct_yaml_seq(self, node):
        obj, = SafeConstructor.construct_yaml_seq(self, node)
        return self._holder(obj, node)

    def construct_yaml_map(self, node):
        obj, = SafeConstructor.construct_yaml_map(self, node)
        return self._holder(obj, node)

    def _holder(self, obj, node):
        return holder.Holder(value=obj,
                             start_line=node.start_mark.line,
                             start_column=node.start_mark.column,
                             end_line=node.end_mark.line,
                             end_column=node.end_mark.column,
                             filename=self.filename)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:null',
    HolderConstructor.construct_yaml_null)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:bool',
    HolderConstructor.construct_yaml_bool)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:int',
    HolderConstructor.construct_yaml_int)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:float',
    HolderConstructor.construct_yaml_float)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:binary',
    HolderConstructor.construct_yaml_binary)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:timestamp',
    HolderConstructor.construct_yaml_timestamp)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:omap',
    HolderConstructor.construct_yaml_omap)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:pairs',
    HolderConstructor.construct_yaml_pairs)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:set',
    HolderConstructor.construct_yaml_set)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:str',
    HolderConstructor.construct_yaml_str)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:seq',
    HolderConstructor.construct_yaml_seq)

HolderConstructor.add_constructor(
    u'tag:yaml.org,2002:map',
    HolderConstructor.construct_yaml_map)


class MarkedLoader(Reader, Scanner, Parser, Composer, HolderConstructor,
                   Resolver):
    def __init__(self, stream, filename=None):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        HolderConstructor.__init__(self, filename)
        Resolver.__init__(self)


def load(stream, filename):
    result = MarkedLoader(stream, filename).get_single_data()
    if result is None:
        # load of empty string returns None so we convert it to an empty
        # dict
        result = holder.Holder.of({}, filename=filename)
    return result
