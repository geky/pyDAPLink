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

from ..errors import CommandError
import client
import logging


# Read modes:
# Start a read. This must be followed by READ_END of the
# same type and in the same order
READ_START = 1
# Read immediately
READ_NOW = 2
# Get the result of a read started with READ_START
READ_END = 3


class DAPLinkClientConnection(object):
    """
    Implements a DAPLink connection to a specific board.
    Returned from DAPLinkClient.getConnectedBoards, 
    must be initialized before use.
    """
    def __init__(self, client, vid, pid, iid):
        self._client = client
        self.vid = vid
        self.pid = pid
        self.iid = iid

        info = self._command('board_info', {'id': iid})
        self.vendor_name = info['vendor']
        self.product_name = info['product']
        self.serial_number = info['serial']

        self._locked = False

        self.deferred_transfer = False
        self._buffer = []

    def __repr__(self):
        return ('<%s %04x:%04x:%x>' % 
                (self.__class__.__name__, self.vid, self.pid, self.iid))

    def _command(self, *args):
        """ Defers command handling to client class. """
        return self._client.command(*args)

    def _select(self):
        if self._locked:
            return

        attempts = 0

        while (not self._lock_attempts or attempts < self._lock_attempts):
            try:
                data = self._command('board_select', {'id': self.iid})

                if data['selected']:
                    return
                else:
                    attempts += 1
            except ServerError as err:
                if err.type == 'KeyError':
                    raise CommandError('Unable to select device %04x:%04x:%x' % 
                                       (self.vid, self.pid, self.iid))
                else:
                    raise
        else:
            raise CommandError('Unable to lock device %04x:%04x:%x, '
                               'may be in use by another process' % 
                               (self.vid, self.pid, self.iid))

    def _deselect(self):
        if self._locked:
            return

        self._command('board_deselect')

    def init(self, frequency=None, lock_attempts=5, new_socket=True):
        """ 
        Initialize daplink connection to a specific device. 

        By default, a new socket connection is created to more easily
        manage devices on the server's end. If new_socket is false,
        the client that created this connection must be kept alive.
        """
        self._lock_attempts = lock_attempts
        self._new_socket = new_socket

        if new_socket:
            self._client = client.DAPLinkClient(self._client.address, False)
            self._client.init()
            self._client.command('board_enumerate', {'vid': self.vid, 'pid': self.pid})

        # We default to locking the device. It can be explicitly unlocked
        # to allow multiprocess access
        self.lock()
        self._command('dap_init', {'frequency': frequency} if frequency else {})

    def uninit(self):
        self._select()
        self._command('dap_uninit')
        self.unlock()

        if self._new_socket:
            self._client.uninit()

    def lock(self):
        """ Locks device for exclusive access from this connection. """
        self._select()
        self._locked = True

    def unlock(self):
        """ Unlocks device. """
        self._locked = False
        self._deselect()

    def info(self, request):
        self._select()
        resp = self._command('dap_info', {'request': request})
        self._deselect()

        if 'result' in resp:
            return resp['result']
        else:
            return None

    def reset(self):
        """ Resets device. """
        self._select()
        self._command('reset')
        self._deselect()

    def assertReset(self, asserted):
        """ Asserts reset on device. """
        self._select()
        if asserted:
            self._command('reset_assert')
        else:
            self._command('reset_deassert')
        self._deselect()

    def setClock(self, frequency):
        self._select()
        self._command('dap_clock', {'frequency': frequency})
        self._deselect()

    def setDeferredTransfer(self, enable):
        """
        Allow transfers to be delayed and buffered

        By default deferred transfers are turned off. All reads and
        writes will be completed by the time the function returns.

        When enabled packets are buffered and sent all at once, which
        increases speed. When memory is written to, the transfer
        might take place immediately, or might take place on a future
        memory write. This means that an invalid write could cause an
        exception to occur on a later, unrelated write. To guarantee
        that previous writes are complete call the flush() function.

        The behaviour of read operations is determined by the modes
        READ_START, READ_NOW and READ_END. The option READ_NOW is the
        default and will cause the read to flush all previous writes,
        and read the data immediately. To improve performance, multiple
        reads can be made using READ_START and finished later with READ_NOW.
        This allows the reads to be buffered and sent at once. Note - All
        READ_ENDs must be called before a call using READ_NOW can be made.
        """
        if self.deferred_transfer and not enable:
            self.flush()

        self.deferred_transfer = enable

    def writeDP(self, addr, data):
        self._select()
        self._command('write_dp', {'addr': addr, 'data': data})
        self._write()
        self._deselect()

    def readDP(self, addr, mode = READ_NOW):
        self._select()
        if mode in (READ_NOW, READ_START):
            self._command('read_dp', {'addr': addr})
        if mode in (READ_NOW, READ_END):
            resp = self._read()
        self._deselect()

        if mode in (READ_NOW, READ_END):
            return resp

    def writeAP(self, addr, data):
        self._select()
        self._command('write_ap', {'addr': addr, 'data': data})
        self._write()
        self._deselect()

    def readAP(self, addr, mode = READ_NOW):
        self._select()
        if mode in (READ_NOW, READ_START):
            self._command('read_ap', {'addr': addr})
        if mode in (READ_NOW, READ_END):
            resp = self._read()
        self._deselect()

        if mode in (READ_NOW, READ_END):
            return resp

    def writeMem(self, addr, data, transfer_size = 32):
        self._select()
        self._command('write_%s' % transfer_size, {'addr': addr, 'data': data})
        self._write()
        self._deselect()

    def readMem(self, addr, transfer_size = 32, mode = READ_NOW):
        self._select()
        if mode in (READ_NOW, READ_START):
            self._command('read_%s' % transfer_size, {'addr': addr})
        if mode in (READ_NOW, READ_END):
            resp = self._read()
        self._deselect()

        if mode in (READ_NOW, READ_END):
            return resp

    def writeBlock32(self, addr, data):
        self._select()
        self._command('write_block', {'addr': addr, 'data': data})
        self._write()
        self._deselect()

    def readBlock32(self, addr, count):
        self._select()
        self._command('read_block', {'addr': addr, 'count': count})
        resp = self._read()
        self._deselect()
        return resp

    def _write(self):
        """
        Complete write command
        """
        if not self.deferred_transfer:
            self._command('flush')

    def _read(self):
        """
        Complete read command of specified size
        """
        if not self._buffer:
            data = self._command('flush')
            self._buffer.extend(data['reads'])

        return self._buffer.pop(0)

    def flush(self):
        """
        Clear buffer and flush server
        """
        self._command('flush')
        self._buffer = []

        
