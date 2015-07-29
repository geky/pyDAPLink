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
from pyDAPLink import DAPLinkServer
from pyDAPLink import DAPLinkClient
from pyDAPLink import DAPLink
from pyDAPLink.socket import SOCKET
from pyDAPLink.interface import INTERFACE
import time


@pytest.fixture
def vid():
    """ VID of device for testing """
    return 0x0d28

@pytest.fixture
def pid():
    """ PID of device for testing """
    return 0x0204

@pytest.fixture(params=[1,2,4,8])
def client_count(request):
    """ Number of clients to test with """
    return request.param

@pytest.fixture(params=SOCKET.keys())
def socket(request):
    """ Type of socket connection to use """
    return request.param

@pytest.fixture(params=INTERFACE.keys())
def interface(request):
    """ Type of interface to use """
    return request.param


class TestConnections:
    def test_single_clients(self, socket, interface, client_count, vid, pid):
        for n in xrange(client_count):
            client = DAPLink(socket=socket, interface=interface)
            client.init()

            boards = client.getConnectedBoards(vid, pid)
            for board in boards:
                assert (board.vid, board.pid) == (vid, pid)

            client.uninit()

    def test_simultaneous_clients(self, socket, interface, client_count, vid, pid):
        clients = []

        for n in xrange(client_count):
            client = DAPLink(socket=socket, interface=interface)
            client.init()
            clients.append(client)

        for client in clients:
            boards = client.getConnectedBoards(vid, pid)
            for board in boards:
                assert (board.vid, board.pid) == (vid, pid)

        for client in clients:
            client.uninit()

    def test_successive_clients(self, socket, interface, client_count, vid, pid):
        client = DAPLink(socket=socket, interface=interface)
        client.init()
        previous = client

        for n in xrange(client_count):
            client = DAPLink()
            client.init()
            previous.uninit()

            boards = client.getConnectedBoards(vid, pid)
            for board in boards:
                assert (board.vid, board.pid) == (vid, pid)

            previous = client

        previous.uninit()

    def test_seperate_server(self, socket, interface, client_count, vid, pid):
        if socket == 'unix':
            address = '/tmp/pydaplink/test-socket'
        else:
            address = 'localhost:1234'

        server = DAPLinkServer(address=address, socket=socket, interface=interface)
        server.init()

        assert server.socket == socket
        assert server.interface == interface
        assert server.address == address
        assert server.client_count == 0

        clients = []

        for n in xrange(client_count):
            client = DAPLinkClient(address=address, socket=socket, 
                                   interface=interface, create_server=False)
            client.init()
            clients.append(client)

            assert client.socket == socket
            assert client.interface == interface
            assert client.address == address

            boards = client.getConnectedBoards(vid, pid)
            for board in boards:
                assert (board.vid, board.pid) == (vid, pid)

        assert server.client_count == client_count

        for client in clients:
            client.uninit()

        server.uninit()

