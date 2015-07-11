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


def init(locals):
    """ Sets up client connection. """
    locals.ifs = None
    locals.id = None

    locals.daplink = None
    locals.dapreads = None

def uninit(locals):
    """ Tears down client connection. """
    if locals.daplink:
        locals.daplink.uninit()
        locals.ifs[locals.id].close()


@command(None, '*')
def sv(locals):
    """ Gets the version of the server. """
    return __version__


@command('HH', None)
def bi(locals, vid, pid):
    """ Set VID and PID to use. """
    ifs = IfSelection(vid, pid)
    ifs.enumerate()

    locals.ifs = ifs

@command(None, '*')
def bl(locals):
    """
    Lists all connected boards with the select VID and PID.
    Lists boards as 16-bit ids which can be used to get more 
    information.
    """
    return ''.join(pack('H', id) for id in locals.ifs.ids())

@command('H', 'B')
def bs(locals, id):
    """ 
    Selects the board with the specified bus and address.
    Returns 0 if board was selected, 1 if board is selected
    by another process, or 2 if the board does not exist.
    """
    locals.id = None

    try:
        if locals.ifs.select(id):
            locals.id = id
            return 0
        else:
            return 1
    except KeyError:
        return 2

@command(None, None)
def bd(locals):
    """ Unselects current board so it can be used by another process. """
    try:
        locals.ifs.deselect(locals.id)
    except KeyError:
        pass

    locals.id = None

@command('H', '*')
def bv(locals, id):
    """ Returns the specified board's vendor name. """
    return locals.ifs[id].vendor_name

@command('H', '*')
def bp(locals, id):
    """ Returns the specified board's product name. """
    return locals.ifs[id].product_name

@command('H', '*')
def bn(locals, id):
    """ Returns the specified board's serial number. """
    return locals.ifs[id].serial_number


@command('I', None)
def li(locals, frequency):
    """ Initializes a DAPLink connection with specified frequency. """
    interface = locals.ifs[locals.id]
    interface.init()
    locals.daplink = DAPLinkCore(interface)
    locals.daplink.init(frequency)
    locals.dapreads = []

@command(None, None)
def lu(locals):
    """ Uninitializes a DAPLink connection. """
    locals.daplink.uninit()
    locals.daplink = None
    locals.dapreads = None
    locals.ifs[locals.id].close()

@command('I', None)
def lc(locals, frequency):
    """ Change a DAPLink connection's frequency. """
    locals.daplink.setClock(frequency)

@command('*', '*')
def lq(locals, query):
    """ Query DAPLink info. """
    result = locals.daplink.info(query)

    if isinstance(result, int):
        return pack('I', result)
    elif result:
        return result
    else:
        return ''

@command(None, None)
def lr(locals):
    """ Resets the device. """
    locals.daplink.reset()

@command(None, None)
def la(locals):
    """ Asserts reset on the device. """
    locals.daplink.assertReset(True)

@command(None, None)
def ld(locals):
    """ Deasserts reset on the device. """
    locals.daplink.assertReset(False)


@command('II', None)
def wd(locals, address, data):
    """ Write to DP. """
    locals.daplink.writeDP(address, data)

@command('I', None)
def rd(locals, address):
    """ Read from DP. """
    locals.daplink.readDP(address)
    locals.dapreads.append(lambda d: pack('I', d))

@command('II', None)
def wa(locals, address, data):
    """ Write to AP. """
    locals.daplink.writeAP(address, data)

@command('I', None)
def ra(locals, address):
    """ Read from AP. """
    locals.daplink.readAP(address)
    locals.dapreads.append(lambda d: pack('I', d))

@command('IB', None)
def w1(locals, address, data):
    """ Writes to an 8-bit memory location. """
    locals.daplink.writeMem(address, data, 8)

@command('I', None)
def r1(locals, address):
    """ Reads an 8-bit memory location. """
    locals.daplink.readMem(address, 8)
    locals.dapreads.append(lambda d: pack('B', d))

@command('IH', None)
def w2(locals, address, data):
    """ Writes to an 16-bit memory location. """
    locals.daplink.writeMem(address, data, 16)

@command('I', None)
def r2(locals, address):
    """ Reads an 16-bit memory location. """
    locals.daplink.readMem(address, 16)
    locals.dapreads.append(lambda d: pack('H', d))

@command('II', None)
def w4(locals, address, data):
    """ Writes to an 32-bit memory location. """
    locals.daplink.writeMem(address, data, 32)

@command('I', None)
def r4(locals, address):
    """ Reads an 32-bit memory location. """
    locals.daplink.readMem(address, 32)
    locals.dapreads.append(lambda d: pack('I', d))

@command('I*', None)
def wb(locals, address, data):
    """ Write word-aligned block to memory. """
    data = [unpack('I', data[i:i+4])[0]
            for i in range(0, len(data), 4)]
    locals.daplink.writeBlock32(address, data)

@command('II', None)
def rb(locals, address, count):
    """ Read word-aligned block from memory. """
    def packBlock(block):
        return ''.join(pack('I', i) for i in block)

    locals.daplink.readBlock32(address, count)
    locals.dapreads.append(packBlock)

@command(None, '*')
def ff(locals):
    """ Flushes and completes transfer,
        responds with all data that has been collected.
    """
    results = locals.daplink.flush()
    reads = locals.dapreads
    locals.dapreads = []

    return ''.join(read(result) for read, result in zip(reads, results))
