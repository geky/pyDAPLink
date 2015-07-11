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
from ..daplink import DAPLinkCore
from .selection import IfSelection
import logging

from .._version import version as __version__


COMMANDS = {}

def command(args_format, resp_format):
    """ 
    Decorator for wrapping commands in pack/unpack calls
    and storing in the COMMANDS table.
    """
    def wrapper(func):
        def converter(daplink, raw_args):
            if args_format:
                args = unpack(args_format, raw_args)
            else:
                args = []

            resp = func(daplink, *args)

            if resp_format:
                if not isinstance(resp, tuple):
                    resp = resp,
                return pack(resp_format, *resp)
            else:
                return ''

        assert func.__name__ not in COMMANDS
        COMMANDS[func.__name__] = converter

    return wrapper



class DAPLinkServerConnection(object):
    def init(self):
        """ Sets up client connection. """
        self.ifs = None
        self.id = None

        self.daplink = None
        self.dapreads = None

    def uninit(self):
        """ Tears down client connection. """
        if self.daplink:
            self.daplink.uninit()
            self.ifs[self.id].close()

    def handle_command(self, command, data):
        if command not in COMMANDS:
            return None

        return COMMANDS[command](self, data)


    # Server configuration
    @command(None, '*')
    def sv(self):
        """ Gets the version of the server. """
        return __version__


    # Board handling
    @command('HH', None)
    def bi(self, vid, pid):
        """ Set VID and PID to use. """
        ifs = IfSelection(vid, pid)
        ifs.enumerate()

        self.ifs = ifs

    @command(None, '*')
    def bl(self):
        """
        Lists all connected boards with the select VID and PID.
        Lists boards as 16-bit ids which can be used to get more 
        information.
        """
        return ''.join(pack('H', id) for id in self.ifs.ids())

    @command('H', 'B')
    def bs(self, id):
        """ 
        Selects the board with the specified bus and address.
        Returns 0 if board was selected, 1 if board is selected
        by another process, or 2 if the board does not exist.
        """
        self.id = None

        try:
            if self.ifs.select(id):
                self.id = id
                return 0
            else:
                return 1
        except KeyError:
            return 2

    @command(None, None)
    def bd(self):
        """ Unselects current board so it can be used by another process. """
        try:
            self.ifs.deselect(self.id)
        except KeyError:
            pass

        self.id = None

    @command('H', '*')
    def bv(self, id):
        """ Returns the specified board's vendor name. """
        return self.ifs[id].vendor_name

    @command('H', '*')
    def bp(self, id):
        """ Returns the specified board's product name. """
        return self.ifs[id].product_name

    @command('H', '*')
    def bn(self, id):
        """ Returns the specified board's serial number. """
        return self.ifs[id].serial_number


    # DAPLink connection
    @command('I', None)
    def li(self, frequency):
        """ Initializes a DAPLink connection with specified frequency. """
        interface = self.ifs[self.id]
        interface.init()
        self.daplink = DAPLinkCore(interface)
        self.daplink.init(frequency)
        self.dapreads = []

    @command(None, None)
    def lu(self):
        """ Uninitializes a DAPLink connection. """
        self.daplink.uninit()
        self.daplink = None
        self.dapreads = None
        self.ifs[self.id].close()

    @command('I', None)
    def lc(self, frequency):
        """ Change a DAPLink connection's frequency. """
        self.daplink.setClock(frequency)

    @command('*', '*')
    def lq(self, query):
        """ Query DAPLink info. """
        result = self.daplink.info(query)

        if isinstance(result, int):
            return pack('I', result)
        elif result:
            return result
        else:
            return ''

    @command(None, None)
    def lr(self):
        """ Resets the device. """
        self.daplink.reset()

    @command(None, None)
    def la(self):
        """ Asserts reset on the device. """
        self.daplink.assertReset(True)

    @command(None, None)
    def ld(self):
        """ Deasserts reset on the device. """
        self.daplink.assertReset(False)


    # Read/write commands
    @command('II', None)
    def wd(self, address, data):
        """ Write to DP. """
        self.daplink.writeDP(address, data)

    @command('I', None)
    def rd(self, address):
        """ Read from DP. """
        self.daplink.readDP(address)
        self.dapreads.append(lambda d: pack('I', d))

    @command('II', None)
    def wa(self, address, data):
        """ Write to AP. """
        self.daplink.writeAP(address, data)

    @command('I', None)
    def ra(self, address):
        """ Read from AP. """
        self.daplink.readAP(address)
        self.dapreads.append(lambda d: pack('I', d))

    @command('IB', None)
    def w1(self, address, data):
        """ Writes to an 8-bit memory location. """
        self.daplink.writeMem(address, data, 8)

    @command('I', None)
    def r1(self, address):
        """ Reads an 8-bit memory location. """
        self.daplink.readMem(address, 8)
        self.dapreads.append(lambda d: pack('B', d))

    @command('IH', None)
    def w2(self, address, data):
        """ Writes to an 16-bit memory location. """
        self.daplink.writeMem(address, data, 16)

    @command('I', None)
    def r2(self, address):
        """ Reads an 16-bit memory location. """
        self.daplink.readMem(address, 16)
        self.dapreads.append(lambda d: pack('H', d))

    @command('II', None)
    def w4(self, address, data):
        """ Writes to an 32-bit memory location. """
        self.daplink.writeMem(address, data, 32)

    @command('I', None)
    def r4(self, address):
        """ Reads an 32-bit memory location. """
        self.daplink.readMem(address, 32)
        self.dapreads.append(lambda d: pack('I', d))

    @command('I*', None)
    def wb(self, address, data):
        """ Write word-aligned block to memory. """
        data = [unpack('I', data[i:i+4])[0]
                for i in range(0, len(data), 4)]
        self.daplink.writeBlock32(address, data)

    @command('II', None)
    def rb(self, address, count):
        """ Read word-aligned block from memory. """
        def packBlock(block):
            return ''.join(pack('I', i) for i in block)

        self.daplink.readBlock32(address, count)
        self.dapreads.append(packBlock)

    @command(None, '*')
    def ff(self):
        """ Flushes and completes transfer,
            responds with all data that has been collected.
        """
        results = self.daplink.flush()
        reads = self.dapreads
        self.dapreads = []

        return ''.join(read(result) for read, result in zip(reads, results))
