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

import socket
import errno


# Creating pairs of sockets for interrupting accept calls
# Workaround for windows, which lacks both pipes and socket.socketpair
def socket_pair():
    if hasattr(socket, 'socketpair'):
        return socket.socketpair()

    server = socket.socket()
    server.bind(('localhost', 0))
    server.listen(1)

    a = socket.socket()
    a.setblocking(False)

    try:
        a.connect(server.getsockname())
    except socket.error as err:
        if err.errno not in (errno.EWOULDBLOCK, errno.EINPROGRESS):
            raise
    
    b, _ = server.accept()

    return a, b
    
