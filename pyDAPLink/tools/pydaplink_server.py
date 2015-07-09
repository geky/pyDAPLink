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


parser = argparse.ArgumentParser(description='pyDAPLink server')
parser.add_argument('--version', action='version', version=__version__)
parser.add_argument('-v', '--verbose', action='store_true', default=False, 
                    help="Enable verbose logging.")
parser.add_argument('-a', '--address', 
                    help="Specify location to use as address for socket.")
parser.add_argument('--temporary', action='store_true', default=False,
                    help="Exit after all clients disconnect.")

def main():
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    server = DAPLinkServer(args.address)
    server.init()
    print 'pyDAPLink server running'

    try:
        if args.temporary:
            while server.client_count < 1:
                sleep(5)

            while server.client_count > 0:
                sleep(5)
        else:
            while True:
                sleep(60*60)
    except KeyboardInterrupt:
        pass
    finally:
        server.uninit()


if __name__ == '__main__':
    main()
