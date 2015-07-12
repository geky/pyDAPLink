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

from .connection import DAPLinkClientConnection
from ..socket import default_client
from ..utility import encode, decode
from ..utility import popen_and_detach
from ..errors import CommandError, ServerError, TransferError
from time import sleep
import logging

from .._version import version as __version__


class DAPLinkClient(object):
    """
    This class implements the DAPLink interface over a socket based
    connection. Communication is performed by sending commands 
    formed as 2-byte command, 2-byte length, and then the command
    specific payload.
    """

    def __init__(self, address=None, create_server=True, connect_attempts=5):
        self._client = default_client(*[address] if address else [])
        self._create_server = create_server
        self._connect_attempts = connect_attempts

    def init(self):
        attempts = 0

        while (not self._connect_attempts or
               attempts < self._connect_attempts):
            try:
                self._client.init()
                break
            except IOError:
                if attempts == 0 and self._create_server:
                    process = popen_and_detach(['pydaplink-server',
                                                '--temporary',
                                                '--address', self.address])
                sleep(0.1)
                attempts += 1
        else:
            raise

        # Check the server's version, this also determines if the server 
        # is actually a daplink server
        server_info = self.command('server_info')

        if server_info['version'] != __version__:
            logging.warning('Server and client are not the same version')

    def uninit(self):
        self._client.uninit()

    @property
    def address(self):
        return self._client.address

    def command(self, command, data={}):
        data['command'] = command

        self._client.send(encode(data))

        resp = decode(self._client.recv())
        if not self._client.isalive():
            raise IOError("Server disconnected")

        if 'error' in resp:
            if resp['error'] == 'CommandError':
                raise CommandError(resp['message'])
            elif resp['error'] == 'TransferError':
                raise TransferError(resp['message'])
            else:
                raise ServerError(resp['error'], resp['message'])
        elif 'response' not in resp or resp['response'] != command:
            raise CommandError("Invalid response")

        return resp

    def getConnectedBoards(self, vid, pid):
        data = self.command('board_enumerate', {'vid': vid, 'pid': pid})

        boards = [DAPLinkClientConnection(self, vid, pid, id)
                  for id in data['ids']]

        return boards

