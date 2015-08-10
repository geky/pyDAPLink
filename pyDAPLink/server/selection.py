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

from ..utility import UniqueType
from ..interface import default_interface
import logging
import threading
from threading import Lock


class IfSelection(object):
    """ A globally unique selection of interfaces based of vid/pid pair """
    __metaclass__ = UniqueType

    def __init__(self, vid, pid):
        self.vid = vid
        self.pid = pid
        self._lock = Lock()
        self._ifs = {}
        self._daplinks = {}
        self._owners = {}

    def enumerate(self, interface=default_interface):
        with self._lock:
            # Find and store all intefaces that match the vid/pid
            # in the cache for the lifetime of this selection.
            # We need to make sure no existing interface's ids change
            new_ifs = interface.getConnectedInterfaces(self.vid, self.pid)

            for new_if in new_ifs or []:
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

            logging.debug('board %d selected' if id not in self._owners else
                          'board %d selected because previous owner is defunct',
                          id)

            self._owners[id] = threading.current_thread()
            return self._ifs[id]

    def deselect(self, id):
        with self._lock:
            del self._owners[id]
            logging.debug('board %d deselected', id)

    def __del__(self):
        for id in self._owners.keys():
            logging.debug('board %d deselected because owner is defunct', id)
