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

from .socket import default_client
from .utility import pack, unpack
from .utility import popen_and_detach
from .errors import CommandError
from time import sleep
import logging


class DAPLinkClient(object):
    """
    This class implements the DAPLink interface over a socket based
    connection. Communication is performed by sending commands 
    formed as 2-byte command, 2-byte length, and then the command
    specific payload.
    """

    def __init__(self, address=None, create_server=True):
        self._client = default_client(*[address] if address else [])
        self._create_server = create_server

    def init(self):
        try:
            self._client.init()
        except IOError:
            if self._create_server:
                popen_and_detach(['pydaplink-server', '--temporary'])
                # give the server some time to create the socket
                sleep(0.5)
                self._client.init()
            else:
                raise

    def _command(self, command, args=None, resp=None, *arglist):
        raw_args = pack(args, *arglist) if args else ''
        self._client.send(pack('2sH*', command, len(raw_args), raw_args))

        data = self._client.recv(4)

        if not self._client.isalive() or len(data) != 4:
            raise IOError("Server disconnected")

        resp_command, size = unpack('2sH', data)
        data = self._client.recv(size) if size > 0 else ''
        
        if not self._client.isalive() or len(data) != size:
            raise IOError("Server disconnected")
        elif resp_command == 'xu':
            raise CommandError('Unsupported command "%s"' % command)
        elif resp_command != command:
            raise CommandError('Error occured during command "%s"' % command)

        if resp:
            resplist = unpack(resp, data)
            return resplist[0] if len(resplist) == 1 else resplist

    def getConnectedBoards(self, vid, pid):
        board_num = 0
        boards = []

        while True:
            selected = self._command('bs', 'HHH', '?', vid, pid, board_num)
            if not selected:
                return boards

            vendor_name = self._command('bv', None, '*')
            product_name = self._command('bp', None, '*')

            boards.append((board_num, vendor_name, product_name))
            board_num += 1

    def uninit(self):
        self._client.uninit()

