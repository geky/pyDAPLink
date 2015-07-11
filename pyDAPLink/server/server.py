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

from .connection import DAPLinkServerConnection
from ..utility import pack, unpack
from ..socket import default_server
import logging
import threading
from threading import Thread
import traceback
import sys



class DAPLinkServer(object):
    """
    This class provides the DAPLink interface as a streaming socket 
    based server. Communication is performed by sending commands
    formed as 2-byte command, 2-byte length, and then the payload.

    Error responses:
    [ 'xu' | len | message ] unsupported command
    [ 'xe' | len | message ] unknown error has occured
    [ 'xx' | len | message ] malformed command
    """

    def __init__(self, address=None):
        self._server = default_server(*[address] if address else [])
        self._threads = set()

    def init(self):
        self._server.init()

        thread = Thread(target=self._server_task)
        thread.daemon = True
        thread.shutdown = lambda: self._server.shutdown()
        thread.start()
        self._threads.add(thread)

    @property
    def client_count(self):
        # Each client gets it's own thread
        return max(len(self._threads)-1, 0)

    @property
    def address(self):
        return self._server.address


    @staticmethod
    def _recv(client):
        data = client.recv(4)

        if not client.isalive():
            return
        elif len(data) < 4:
            raise CommandError('Malformed command')

        command, size = unpack('2sH', data)
        data = client.recv(size) if size > 0 else ''

        if not client.isalive():
            return
        elif len(data) != size:
            raise CommandError('Malformed command: %s' % command)

        return command, data

    @staticmethod
    def _send(client, command, data):
        client.send(pack('2sH*', command, len(data), data))


    def _server_task(self):
        try:
            while self._server.isalive():
                client = self._server.accept()

                if client:
                    thread = Thread(target=lambda: self._client_task(client))
                    thread.daemon = True
                    thread.shutdown = lambda: client.shutdown()
                    thread.start()
                    self._threads.add(thread)
        finally:
            self._threads.discard(threading.current_thread())

    def _client_task(self, client):
        connection = DAPLinkServerConnection()
        connection.init()

        try:
            while True:
                try:
                    command = self._recv(client)
                except CommandError as err:
                    self._send(client, 'xx', str(err))
                    continue

                if not client.isalive():
                    break

                try:
                    resp = connection.handle_command(command[0], command[1])
                except:
                    exc = sys.exc_info()
                    message = traceback.format_exception_only(exc[0], exc[1])[-1]
                    logging.error(message)
                    self._send(client, 'xe', message)
                    continue

                if resp is None:
                    self._send(client, 'xu', 'Unsupported command: %s' % command)
                    continue

                self._send(client, command[0], resp)

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

        self._server.uninit()

