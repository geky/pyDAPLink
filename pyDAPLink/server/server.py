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

from ..utility import pack, unpack
from ..socket import default_server
import logging
import threading
from threading import Thread
import traceback
import sys
import os

from .commands import COMMANDS


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
        self.locals = threading.local()

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
        try:
            while True:
                data = client.recv(4)

                if not client.isalive():
                    break
                elif len(data) < 4:
                    message = 'Malformed command'
                    client.send(pack('2sH*', 'xx', len(message), message))
                    continue
               
                command, size = unpack('2sH', data)
                data = client.recv(size) if size > 0 else ''

                if not client.isalive():
                    break
                elif len(data) != size:
                    message = 'Malformed command'
                    client.send(pack('2sH*', 'xx', len(message), message))
                    continue

                self._handle_command(client, command, data)
        finally:
            client.close()
            self._threads.discard(threading.current_thread())
        
    def _handle_command(self, client, command, data):
        if command not in COMMANDS:
            message = 'Unsupported command: %s' % command
            client.send(pack('2sH*', 'xu', len(message), message))
            return

        try:
            resp = COMMANDS[command](self.locals, data)
        except:
            try:
                exc = sys.exc_info()
                message = traceback.format_exception_only(exc[0], exc[1])[-1]
                logging.error(message)
                client.send(pack('2sH*', 'xe', len(message), message))
            except:
                pass
        else:
            client.send(pack('2sH*', command, len(resp), resp))

    def uninit(self):
        threads = self._threads.copy()
        for thread in threads:
            thread.shutdown()
        for thread in threads:
            thread.join()

        self._server.uninit()


