#!/usr/bin/env python
"""
 mbed CMSIS-DAP debugger
 Copyright (c) 2015 ARM Limited

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

import argparse
import logging
import sys
from time import sleep

import pyDAPLink
from pyDAPLink import __version__
from pyDAPLink import DAPLinkServer
from pyDAPLink.socket import SOCKET
from pyDAPLink.interface import INTERFACE


parser = argparse.ArgumentParser(description='pyDAPLink server')
parser.add_argument('--version', action='version', version=__version__)
parser.add_argument('-v', '--verbose', action='count', default=0,
                    help="Enable verbose logging.")
parser.add_argument('-a', '--address', 
                    help="Specify location to use as address for socket.")
parser.add_argument('-s', '--socket', choices=SOCKET.keys(),
                    help="Specify socket type.")
parser.add_argument('-i', '--interface', choices=INTERFACE.keys(),
                    help="Specify interface.")
parser.add_argument('--temporary', action='store_true', default=False,
                    help="Exit if no clients are connected.")

def main():
    args = parser.parse_args()
    
    if args.verbose > 1:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose > 0:
        logging.basicConfig(level=logging.INFO)

    server = DAPLinkServer(args.address, 
                           socket=args.socket, 
                           interface=args.interface)
    server.init()
    print 'pyDAPLink server running'

    try:
        if args.temporary:
            while True:
                sleep(5)

                if server.client_count == 0:
                    break
        else:
            while True:
                sleep(60*60)
    except KeyboardInterrupt:
        pass
    finally:
        server.uninit()


if __name__ == '__main__':
    main()
