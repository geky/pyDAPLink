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

from threading import Lock
from weakref import WeakValueDictionary


class UniqueType(type):
    """ Metaclass for types that are globally unique for arguments. """
    def __init__(cls, *args, **kw):
        super(UniqueType, cls).__init__(*args, **kw)
        cls.instances = WeakValueDictionary()
        cls.lock = Lock()

    def __call__(cls, *args):
        with cls.lock:
            if args in cls.instances:
                return cls.instances[args]
            else:
                instance = cls.__new__(cls, *args)
                instance.__init__(*args)
                cls.instances[args] = instance
                return instance

