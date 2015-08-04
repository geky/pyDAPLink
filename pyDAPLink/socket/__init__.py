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

from unix_socket import UnixSocket
from tcp_socket import TCPSocket

SOCKET = \
    { socket.name: socket 
      for socket in (UnixSocket, TCPSocket)
      if socket.available }

# Default sockets defined in order of preference
default_socket = \
    next(SOCKET[name] 
         for name in ('unix', 'tcp') 
         if name in SOCKET)

def socket_by_address(address):
    for name in ('unix', 'tcp'):
        if name in SOCKET and SOCKET[name].addrisvalid(address):
            return SOCKET[name]
