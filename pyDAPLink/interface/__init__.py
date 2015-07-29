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

import os
import logging
from hidapi_backend import HidApiUSB
from pyusb_backend import PyUSB
from pywinusb_backend import PyWinUSB

INTERFACE = \
    { backend.name: backend
      for backend in (HidApiUSB, PyUSB, PyWinUSB)
      if backend.available }

# Default interfaces defined in order of preference
default_interface = \
    next(INTERFACE[name]
         for name in ('hidapiusb', 'pyusb', 'pywinusb')
         if name in INTERFACE)

