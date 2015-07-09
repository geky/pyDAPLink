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
import stat
import socket
from .socket import Connection, Server, Client


isAvailable = hasattr(socket, 'AF_UNIX')

class UnixConnection(Connection):
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

class UnixClient(UnixConnection, Client):
    def __init__(self, address='/tmp/pydaplink/socket', timeout=None):
        self.address = address
        self._isalive = False
        self._timeout = timeout

    def init(self):
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.settimeout(self._timeout)
        conn.connect(self.address)

        UnixConnection.__init__(self, conn)

class UnixServer(Server):
    def __init__(self, address='/tmp/pydaplink/socket', timeout=None):
        self.address = address
        self._isalive = False
        self._timeout = timeout
    
    def init(self):
        # First make sure path to socket exists
        try:
            os.makedirs(os.path.dirname(self.address))
        except OSError:
            pass

        # Socket can get left if previous server failed to exit cleanly
        try:
            if stat.S_ISSOCK(os.stat(self.address).st_mode):
                os.unlink(self.address)
        except OSError:
            pass

        # Create the server socket
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.settimeout(self._timeout)
        self._socket.bind(self.address)
        self._socket.listen(socket.SOMAXCONN)

        self._isalive = True

    def accept(self):
        conn, _ = self._socket.accept()
        conn.settimeout(self._timeout)

        if self._isalive:
            return UnixConnection(conn)
        else:
            return None

    def isalive(self):
        return self._isalive

    def shutdown(self):
        self._isalive = False
        # Create connection to wake up accept call
        conn = UnixClient(self.address)
        conn.init()
        conn.uninit()

    def uninit(self):
        self._socket.close()
        os.unlink(self.address)

