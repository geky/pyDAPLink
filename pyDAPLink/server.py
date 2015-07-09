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

from .daplink import DAPLinkCore
from .interface import INTERFACE, usb_backend
from .socket import default_server
from .utility import pack, unpack
import logging
import threading
from threading import Thread, Lock
from weakref import WeakValueDictionary, WeakSet
from time import sleep
import traceback
import sys
import os


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


@command(None, None)
def pp(locals):
    """ Pings server with no side effects """
    pass

@command('HH', None)
def bi(locals, vid, pid):
    """ Set VID and PID to use. """
    ifs = IfSelection(vid, pid)
    ifs.enumerate()

    locals.ifs = ifs
    locals.id = None

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


class IfSelection(object):
    selections = WeakValueDictionary()
    selections_lock = Lock()

    def __new__(cls, vid, pid):
        with IfSelection.selections_lock:
            if (vid, pid) in IfSelection.selections:
                return IfSelection.selections[vid, pid]
            else:
                selection = super(IfSelection, cls).__new__(cls, vid, pid)
                IfSelection.selections[vid, pid] = selection
                return selection

    def __init__(self, vid, pid):
        self.vid = vid
        self.pid = pid
        self._lock = Lock()
        self._ifs = {}
        self._daplinks = {}
        self._owners = {}

    def enumerate(self):
        with self._lock:
            # Find and store all intefaces that match the vid/pid
            # in the cache for the lifetime of this selection.
            # We need to make sure no existing interface's ids change
            new_ifs = INTERFACE[usb_backend].getConnectedInterfaces(self.vid, self.pid)

            for new_if in new_ifs:
                if new_if not in self._ifs.values():
                    new_id = next(id for id in xrange(1, 2**16)
                                  if id not in self._ifs)

                    self._ifs[new_id] = new_if

    def ids(self):
        with self._lock:
            return self._ifs.keys()

    def __getitem__(self, id):
        with self._lock:
            return self._ifs[id]

    def select(self, id):
        with self._lock:
            if id not in self._ifs:
                raise KeyError(id)

            if id in self._owners and self._owners[id].is_alive():
                return None

            self._owners[id] = threading.current_thread()
            return self._ifs[id]

    def deselect(self, id):
        with self._lock:
            del self._owners[id]


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
            self._threads.remove(threading.current_thread())

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
            self._threads.remove(threading.current_thread())
        
    def _handle_command(self, client, command, data):
        if command not in COMMANDS:
            message = 'Unsupported command: %s' % command
            client.send(pack('2sH*', 'xu', len(message), message))
            return

        try:
            resp = COMMANDS[command](self.locals, data)
        except:
            exc = sys.exc_info()
            try:
                message = traceback.format_exception_only(exc[0], exc[1])
                client.send(pack('2sH*', 'xe', len(message), message))
            except:
                pass
            raise exc[0], exc[1], exc[2]
        else:
            client.send(pack('2sH*', command, len(resp), resp))

    def uninit(self):
        threads = self._threads.copy()
        for thread in threads:
            thread.shutdown()
        for thread in threads:
            thread.join()

        self._server.uninit()


