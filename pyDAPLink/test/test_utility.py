"""
 mbed CMSIS-DAP debugger
 Copyright (c) 2006-2013 ARM Limited

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import pytest
from pyDAPLink.utility import encode, decode
from pyDAPLink.utility import UniqueType
from pyDAPLink.utility import socket_pair
from random import randint
import string
import select


class TestEncodings:
    @pytest.mark.parametrize('command_type', ['command', 'response', 'error'])
    def test_encodings(self, command_type):
        command = {command_type: 'write',
                   'none': None,
                   'bool': True,
                   'str': string.printable,
                   'int': 0x87654321,
                   'list': range(100)}

        encoding = encode(command)
        assert isinstance(encoding, str)
        decoding = decode(encoding)
        assert isinstance(decoding, dict)

        assert decoding == command
        assert decoding['none'] is None
        assert isinstance(decoding['bool'], bool)
        assert isinstance(decoding['str'],  basestring)
        assert isinstance(decoding['int'],  int)
        assert isinstance(decoding['list'], list)


class TestUniqueType:
    @pytest.mark.parametrize('arg_count', [1, 2, 4])
    def test_unique_type(self, arg_count):
        class TestClass(object):
            __metaclass__ = UniqueType

            def __init__(self, *args):
                self.args = args

        argset = set()
        instances = []

        for i in xrange(50):
            args = tuple(randint(0, 4) for i in xrange(randint(0, arg_count)))
            argset.add(args)

            instance = TestClass(*args)
            assert hasattr(instance, 'args')
            assert instance.args == args
            instances.append(instance)

        for args in argset:
            argid = id(TestClass(*args))

            assert all(id(instance) == argid 
                       for instance in instances
                       if instance.args == args)

class TestSocketPair:
    @pytest.mark.parametrize('order', [(0, 1), (1, 0)])
    def test_socket_pair(self, order):
        data = 'Hello World'
        pair = socket_pair()

        pair[order[0]].sendall(data)
        ready, _, _ = select.select([pair[0], pair[1]], [], [])
        assert len(ready) == 1 and ready[0] == pair[order[1]]
        resp = pair[order[1]].recv(64)
        assert resp == data

