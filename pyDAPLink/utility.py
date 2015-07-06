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

import struct
from subprocess import Popen
import sys
import os

# slightly different packing/unpacking to handle multiple args
def pack(fmt, *args):
    if fmt.endswith('*'):
        return struct.pack('!'+fmt[:-1], *args[:-1]) + args[-1]
    else:
        return struct.pack('!'+fmt, *args)

def unpack(fmt, string):
    if fmt.endswith('*'):
        return (struct.unpack_from('!'+fmt[:-1], string) +
                (string[struct.calcsize('!'+fmt[:-1]):],))
    else:
        return struct.unpack('!'+fmt, string)


# Creating and disowning processes
def popen_and_detach(args):
    if not sys.platform.startswith('win'):
        args.insert(0, 'nohup')

    with open(os.devnull, 'w') as null:
        process = Popen(args, stdout=null, stderr=null)

