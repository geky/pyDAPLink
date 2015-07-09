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

class Connection(object):
    def send(self, data):
        return

    def recv(self, size):
        return

    def settimeout(self, timeout):
        return

    def isalive(self):
        return

    def shutdown(self):
        return

    def close(self):
        return

class Client(Connection):
    def __init__(self, address=None, timeout=None):
        self.address = address

    def init(self):
        return

class Server(object):
    def __init__(self, address=None, timeout=None):
        self.address = address
    
    def init(self):
        return

    def accept(self):
        return

    def settimeout(self):
        return

    def isalive(self):
        return

    def shutdown(self):
        return

    def close(self):
        return

