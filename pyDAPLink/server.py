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
from threading import Thread
from time import sleep
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
def pp(server):
    """ Pings server with no side effects """
    pass

@command('HHH', '?')
def bs(server, vid, pid, number):
    """ 
    Selects the nth board with the specified vid and pid.
    Returns 1 if selected or 0 if board does not exist.
    """
    ifs = INTERFACE[usb_backend].getConnectedInterfaces(vid, pid)

    if number >= len(ifs):
        server._select_if(None)
        return False
    
    server._select_if(ifs[number])
    return True

@command(None, '?')
def bl(server):
    """ 
    Tries to lock current board so only the current socket 
    can perform transactions with it.
    Returns 1 if locked or 0 if board is already locked.
    """
    raise NotImplementedError()

@command(None, None)
def bu(server):
    """ Unlocks current board so it can be used by another process. """
    raise NotImplementedError()
    
@command(None, '*')
def bv(server):
    """ Returns the current board's vendor name. """
    return server._current_if().vendor_name

@command(None, '*')
def bp(server):
    """ Returns the current board's product name. """
    return server._current_if().product_name


class DAPLinkServer(object):
    """
    This class provides the DAPLink interface as a streaming socket 
    based server. Communication is performed by sending commands
    formed as 2-byte command, 2-byte length, and then the payload.

    Error responses:
    [ 'xu' | 2 | failed command ] unsupported command
    [ 'xe' | 2 | failed command ] unknown error has occured
    [ 'xx' | 0 ] malformed command
    """

    def __init__(self, address=None):
        self._server = default_server(*[address] if address else [])
        self._threads = set()
        self._ifs = {}

    def init(self):
        self._server.init()

        thread = Thread(target=self._server_task)
        thread.daemon = True
        thread.shutdown = lambda: self._server.shutdown()
        thread.start()
        self._threads.add(thread)

    def client_count(self):
        # Each client gets it's own thread
        return max(len(self._threads)-1, 0)

    def _select_if(self, interface):
        if interface:
            self._ifs[threading.current_thread()] = interface
        else:
            del self._ifs[threading.current_thread()]

    def _current_if(self):
        return self._ifs[threading.current_thread()]

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
            thread = threading.current_thread()
            self._threads.remove(thread)

    def _client_task(self, client):
        try:
            while True:
                data = client.recv(4)

                if not client.isalive():
                    break
                elif len(data) < 4:
                    client.send(pack('2sH', 'xx', 0))
                    continue
               
                command, size = unpack('2sH', data)
                data = client.recv(size) if size > 0 else ''

                if not client.isalive():
                    break
                elif len(data) != size:
                    client.send(pack('2sH', 'xx', 0))
                    continue

                self._handle_command(client, command, data)
        finally:
            client.close()
            thread = threading.current_thread()

            self._threads.remove(thread)
            if thread in self._ifs:
                del self._ifs[thread]
        
    def _handle_command(self, client, command, data):
        if command not in COMMANDS:
            client.send(pack('2sH2s', 'xu', 2, command))
            return

        try:
            resp = COMMANDS[command](self, data)
        except:
            exc_info = sys.exc_info()
            try:
                client.send(pack('2sH2s', 'xe', 2, command))
            except:
                pass
            raise exc_info[0], exc_info[1], exc_info[2]
        else:
            client.send(pack('2sH*', command, len(resp), resp))

    def uninit(self):
        threads = self._threads.copy()
        for thread in threads:
            thread.shutdown()
        for thread in threads:
            thread.join()

        self._server.uninit()


