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

from .transport import DAPLinkServerTransport
from ..utility import encode, decode
from ..errors import CommandError
from ..interface import INTERFACE, default_interface
from ..socket import SOCKET, socket_by_address, default_socket
import logging
import threading
from threading import Thread
import traceback
import sys


class DAPLinkServer(object):
    """
    This class provides the DAPLink interface as a streaming socket 
    based server. Communication is performed by sending commands
    formed as JSON dictionaries.
    """
    def __init__(self, address=None, socket=None, interface=None):
        if interface:
            self._interface = INTERFACE[interface]
        else:
            self._interface = default_interface

        if socket:
            socket = SOCKET[socket]
        elif address:
            socket = socket_by_address(address)
        else:
            socket = default_socket

        if address:
            self._server = socket.Server(address)
        else:
            self._server = socket.Server()

        self.interface = self._interface.name
        self.socket = socket.name
        self._threads = set()

    def init(self):
        self._server.open()

        thread = Thread(target=self._server_task)
        thread.daemon = True
        thread.shutdown = self._server.shutdown
        thread.start()
        self._threads.add(thread)

    @property
    def client_count(self):
        # Each client gets it's own thread
        return max(len(self._threads)-1, 0)

    @property
    def address(self):
        return self._server.address


    def _server_task(self):
        try:
            while self._server.isalive():
                client = self._server.accept()

                if client:
                    thread = Thread(target=lambda: self._client_task(client))
                    thread.daemon = True
                    thread.shutdown = client.shutdown
                    thread.start()
                    self._threads.add(thread)
        finally:
            self._threads.discard(threading.current_thread())

    def _client_task(self, client):
        connection = DAPLinkServerTransport(self._interface)
        connection.init()

        try:
            while True:
                try:
                    try:
                        data = client.recv()
                        if not client.isalive():
                            break

                        data = decode(data)
                    except:
                        raise CommandError('Malformed command')

                    resp = connection.handle(data)
                except:
                    exc = sys.exc_info()
                    type = exc[0].__name__
                    message = str(exc[1])
                    logging.error('%s: %s' % (type, message))

                    try:
                        client.send(encode({'error': type, 'message': message}))
                    except:
                        break
                    else:
                        continue

                client.send(encode(resp))
        finally:
            connection.uninit()
            client.close()
            self._threads.discard(threading.current_thread())


    def uninit(self):
        threads = self._threads.copy()
        for thread in threads:
            thread.shutdown()
        for thread in threads:
            thread.join()

        self._server.close()

