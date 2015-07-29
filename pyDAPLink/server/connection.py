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

from ..daplink import DAPLinkCore
from ..errors import CommandError
from .selection import IfSelection
import logging

from .._version import version as __version__


COMMANDS = {}

def command(func):
    """
    Decorator for handling commands.
    """
    command = func.__name__

    def wrapper(connection, data):
        assert data['command'] == command

        resp = func(connection, data) or {}

        resp['response'] = command
        return resp

    assert command not in COMMANDS
    COMMANDS[command] = wrapper


class DAPLinkServerConnection(object):
    def init(self):
        """ Sets up client connection. """
        self.ifs = None
        self.id = None
        self.dap = None

        logging.info('client connected')

    def uninit(self):
        """ Tears down client connection. """
        if self.dap:
            interface = self.dap.interface
            self.dap.uninit()
            interface.close()

        logging.info('client disconnected')

    def handle(self, data):
        if data['command'] not in COMMANDS:
            raise CommandError('Unsupported command: %s' % data['command'])

        logging.debug('command: %s', data['command'])
        return COMMANDS[data['command']](self, data)


    # Server information
    @command
    def server_info(self, data):
        """ Gets the version of the server. """
        return {'version': __version__}


    # Board handling
    @command
    def board_enumerate(self, data):
        """ 
        Sets VID and PID to use.

        Lists all connected boards with the specified VID/PID
        as 16-bit IDs which can be used to get more information.
        """
        ifs = IfSelection(data['vid'], data['pid'])
        ifs.enumerate()

        self.ifs = ifs
        return {'ids': self.ifs.ids()}

    @command
    def board_select(self, data):
        """
        Selects board with specified id.
        Response is false if board is selected by another process.
        """
        # Erase id so it doesn't accidentally get used if error occurs
        self.id = None

        if self.ifs.select(data['id']):
            self.id = data['id']
            return {'selected': True}
        else:
            return {'selected': False}

    @command
    def board_deselect(self, data):
        try:
            self.ifs.deselect(self.id)
        except KeyError:
            pass

        self.id = None

    @command
    def board_info(self, data):
        """ 
        Returns the specified board's vendor name, product name,
        and serial number.
        """
        interface = self.ifs[data['id']]

        return {'vendor':  interface.vendor_name,
                'product': interface.product_name,
                'serial':  interface.serial_number}


    # DAPLink connection
    @command
    def dap_init(self, data):
        """ 
        Initializes a DAPLink connection. 
        The DAP uses the frequency if specified
        """
        freq = data.get('frequency')

        interface = self.ifs[self.id]
        interface.open()
        self.dap = DAPLinkCore(interface)
        self.dap.init(*[freq] if freq else [])

    @command
    def dap_uninit(self, data):
        """ Uninitializes a DAPLink connection. """
        interface = self.dap.interface
        self.dap.uninit()
        self.dap = None
        interface.close()

    @command
    def dap_clock(self, data):
        """ Change a DAPLink connection's frequency. """
        self.dap.setClock(data['frequency'])

    @command
    def dap_info(self, data):
        """ Queries DAPLink info. """
        result = self.dap.info(data['request'])
        return {'result': result}


    # Reset handling
    @command
    def reset(self, data):
        """ Resets the device. """
        self.dap.reset()

    @command
    def reset_assert(self, data):
        """ Asserts reset on the device. """
        self.dap.assertReset(True)

    @command
    def reset_deassert(self, data):
        """ Deasserts reset on the device. """
        self.dap.assertReset(False)


    # Read/write commands
    @command
    def write_dp(self, data):
        """ Write to DP. """
        self.dap.writeDP(data['addr'], data['data'])

    @command
    def read_dp(self, data):
        """ Read from DP. """
        self.dap.readDP(data['addr'])

    @command
    def write_ap(self, data):
        """ Write to AP. """
        self.dap.writeAP(data['addr'], data['data'])

    @command
    def read_ap(self, data):
        """ Read from AP. """
        self.dap.readAP(data['addr'])

    @command
    def write_8(self, data):
        """ Writes to an 8-bit memory location. """
        self.dap.writeMem(data['addr'], data['data'], 8)

    @command
    def read_8(self, data):
        """ Reads an 8-bit memory location. """
        self.dap.readMem(data['addr'], 8)

    @command
    def write_16(self, data):
        """ Writes to an 16-bit memory location. """
        self.dap.writeMem(data['addr'], data['data'], 16)

    @command
    def read_16(self, data):
        """ Reads an 16-bit memory location. """
        self.dap.readMem(data['addr'], 16)

    @command
    def write_32(self, data):
        """ Writes to an 32-bit memory location. """
        self.dap.writeMem(data['addr'], data['data'], 32)

    @command
    def read_32(self, data):
        """ Reads an 32-bit memory location. """
        self.dap.readMem(data['addr'], 32)

    @command
    def write_block(self, data):
        """ 
        Write word-aligned block to memory. 
        Data must be an array of words.
        """
        self.dap.writeBlock32(data['addr'], data['data'])

    @command
    def read_block(self, data):
        """ 
        Read word-aligned block from memory. 
        Number of words must be specified in count.
        """
        self.dap.readBlock32(data['addr'], data['count'])


    # Flush command obtains data from previous reads and 
    # garuntees execution of previous writes
    @command
    def flush(self, data):
        """ 
        Flushes and completes transfer.
        Responds with all data that has been collected.
        """
        reads = self.dap.flush()

        if reads:
            return {'reads': reads}
