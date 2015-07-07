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

# Needed for importing both socket and .socket
from __future__ import absolute_import

import os
import socket
from select import select
from .socket import Connection, Server, Client


isAvailable = True

def getaddrinfo(address):
    """ Looks up family, type, and underlying ip address for
        the 'hostname:port' address string representation
    """
    # parse host and port values
    host, port = address.rsplit(':', 1)
    port = int(port)
    if host.startswith('[') and host.endswith(']'):
        host = host[1:-1]

    # lookup hostname
    info = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    family, type, _, _, address = info[0]

    return family, type, address

class TCPConnection(Connection):
    def __init__(self, socket):
        self._socket = socket
        self._isalive = True

    def send(self, data):
        self._socket.sendall(data)

    def recv(self, size):
        data = self._socket.recv(size)
        if not data:
            self._isalive = False

        return data

    def isalive(self):
        return self._isalive

    def shutdown(self):
        self._socket.shutdown(2)
        self._isalive = False

    def uninit(self):
        self._socket.close()

class TCPClient(TCPConnection, Client):
    def __init__(self, address='localhost:4116'):
        self.address = address
        self._isalive = False

    def init(self):
        family, type, address = getaddrinfo(self.address)
        conn = socket.socket(family, type)
        conn.connect(address)

        TCPConnection.__init__(self, conn)

class TCPServer(Server):
    def __init__(self, address='localhost:4116'):
        self.address = address
        self._isalive = False
    
    def init(self):
        # Create the server socket
        family, type, address = getaddrinfo(self.address)
        self._socket = socket.socket(family, type)
        self._socket.bind(address)
        self._socket.listen(socket.SOMAXCONN)

        self._port = address[1]
        self._isalive = True

    def accept(self):
        conn, _ = self._socket.accept()

        if self._isalive:
            return TCPConnection(conn)
        else:
            return None

    def isalive(self):
        return self._isalive

    def shutdown(self):
        self._isalive = False
        # Create connection to wake up accept call
        conn = TCPClient('localhost:%d' % self._port)
        conn.init()
        conn.uninit()

    def uninit(self):
        self._socket.close()

