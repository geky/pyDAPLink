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

from subprocess import Popen
from collections import OrderedDict
import json
import sys
import os


# Encoding and decoding of data over the network.
# Expects all parameters to be in an instance of dictionary
def encode(data):
    assert isinstance(data, dict)

    # Even though ordered is unspecified, we put the 
    # command/response/error keys in front to help with debugging
    def isnt_special(entry):
        return entry[0] not in ('command', 'response', 'error')

    ordered = OrderedDict(sorted(data.iteritems(), key=isnt_special))
    return json.dumps(ordered, separators=(',',':')) + '\n'

def decode(data):
    data = json.loads(data)
    assert isinstance(data, dict)
    return data


# Creating and disowning processes
def popen_and_detach(args):
    # Fortunately, OSs without setsid won't need to disown children
    setsid = os.setsid if hasattr(os, 'setsid') else None

    with open(os.devnull, 'w') as null:
        return Popen(args, preexec_fn=setsid, stdout=null, stderr=null)
