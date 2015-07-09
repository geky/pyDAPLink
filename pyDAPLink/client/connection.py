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


class DAPLinkConnection(object):
    """
    Implements a DAPLink connection to a specific board.
    """
    def __init__(self, client, vid, pid, iid):
        self._client = client
        self.vid = vid
        self.pid = pid
        self.iid = iid

        self.vendor_name = self._command('bv', 'H', '*', iid)
        self.product_name = self._command('bp', 'H', '*', iid)
        self.serial_number = self._command('bn', 'H', '*', iid)

        self._locked = False

    def __repr__(self):
        return ('<%s %04x:%04x:%x>' % 
                (self.__class__.__name__, self.vid, self.pid, self.iid))

    def _command(self, *args):
        """ Defers command handling to client class. """
        return self._client._command(*args)

    def _select(self):
        if self._locked:
            return

        attempts = 0

        while (not self._lock_attempts or attempts < self._lock_attempts):
            resp = self._command('bs', 'H', 'B', self.iid)

            if resp == 0:
                return
            elif resp == 1:
                attempts += 1
            else:
                raise CommandError('Unable to select device %04x:%04x:%x' % 
                                   (self.vid, self.pid, self.iid))
        else:
            raise CommandError('Unable to lock device %04x:%04x:%x, '
                               'may be in use by another process' % 
                               (self.vid, self.pid, self.iid))

    def _deselect(self):
        if self._locked:
            return

        self._command('bd')

    def init(self, frequency=1000000, lock_attempts=5, new_socket=True):
        """ Initialize daplink connection to a specific device. 

            By default, a new socket connection is created to more easily
            manage devices on the server's end. If new_socket is false,
            the client that created this connection must be kept alive.
        """
        self._lock_attempts = lock_attempts
        self._new_socket = new_socket

        if new_socket:
            self._client = client.DAPLinkClient(self._client.address, False)
            self._client.init()
            self._client._command('bi', 'HH', None, self.vid, self.pid)

        # We default to locking the device. It can be explicitly unlocked
        # to allow multiprocess access
        self.lock()
        self._command('li', 'I', None, frequency)

    def uninit(self):
        self._select()
        self._command('lu')
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

    def reset(self):
        """ Resets device. """
        self._select()
        self._command('rr')
        self._deselect()

    def assertReset(self, asserted):
        """ Asserts reset on device. """
        self._select()
        if asserted:
            self._command('ra')
        else:
            self._command('rd')
        self._deselect()

