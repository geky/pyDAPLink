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
from .socket import Connection, Server, Client, Socket
from ..utility import socket_pair


class TCPConnection(Connection):
    def __init__(self, socket):
        self._socket = socket
        self._isalive = True

    def send(self, data):
        self._socket.sendall(data)

    def recv(self, size=2**16):
        data = self._socket.recv(size)
        if not data:
            self._isalive = False

        return data

    def settimeout(self, timeout):
        self._socket.settimeout(timeout)

    def isalive(self):
        return self._isalive

    def shutdown(self):
        self._isalive = False
        try:
            self._socket.shutdown(2)
        except socket.error:
            pass

    def uninit(self):
        self._socket.close()

class TCPClient(TCPConnection, Client):
    def __init__(self, address='localhost:4116', timeout=None):
        self.address = address
        self._isalive = False
        self._timeout = timeout

    def init(self):
        family, type, address = TCPSocket.getaddrinfo(self.address)
        conn = socket.socket(family, type)
        conn.settimeout(self._timeout)
        conn.connect(address)

        TCPConnection.__init__(self, conn)

class TCPServer(Server):
    # defaults to restricting access to localhost if remote access
    # is needed, an address without hostname, such as ':4116', can be used
    def __init__(self, address='localhost:4116', timeout=None):
        self.address = address
        self._isalive = False
        self._timeout = timeout
    
    def init(self):
        # Create internal socket so we can interrupt our own accept call
        self._shutdown_pipe = socket_pair()

        # Create the server socket
        family, type, address = TCPSocket.getaddrinfo(self.address)
        self._socket = socket.socket(family, type)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.settimeout(self._timeout)
        self._socket.bind(address)
        self._socket.listen(socket.SOMAXCONN)

        self._port = address[1]
        self._isalive = True

    def accept(self):
        select([self._socket, self._shutdown_pipe[1]], [], [])

        if not self._isalive:
            return None

        conn, _ = self._socket.accept()
        conn.settimeout(self._timeout)
        return TCPConnection(conn)

    def settimeout(self, timeout):
        self._socket.settimeout(timeout)

    def isalive(self):
        return self._isalive

    def shutdown(self):
        self._isalive = False
        # Use pipe to interrupt accept call
        self._shutdown_pipe[0].sendall('shutdown')

    def uninit(self):
        self._socket.close()
        self._shutdown_pipe[0].close()
        self._shutdown_pipe[1].close()


class TCPSocket(Socket):
    name = 'tcp'
    available = True

    @staticmethod
    def addrisvalid(address):
        try:
            TCPSocket.getaddrinfo(address)
            return True
        except:
            return False

    @staticmethod
    def getaddrinfo(address):
        """ 
        Looks up family, type, and underlying ip address for
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

    Client = TCPClient
    Server = TCPServer

