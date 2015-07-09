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
            
        COMMANDS[func.__name__] = converter

    return wrapper


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
    if hasattr(locals, 'id'):
        del locals.id

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
    locals.daplink = DAPLinkCore(interface)
    locals.daplink.init(frequency)

@command(None, None)
def lu(locals):
    """ Uninitializes a DAPLink connection. """
    locals.daplink.uninit()
    del locals.daplink

@command('I', None)
def lc(locals, frequency):
    """ Change a DAPLink connection's frequency. """
    locals.daplink.setClock(frequency)


@command(None, None)
def rr(locals):
    """ Resets the device. """
    locals.daplink.reset()

@command(None, None)
def ra(locals):
    """ Asserts reset on the device. """
    locals.daplink.assertReset(True)

@command(None, None)
def rd(locals):
    """ Deasserts reset on the device. """
    locals.daplink.assertReset(False)


