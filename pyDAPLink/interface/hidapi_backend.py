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

from interface import Interface
import logging, os

try:
    import hid
except:
    if os.name == "posix" and os.uname()[0] == 'Darwin':
        logging.error("cython-hidapi is required on a Mac OS X Machine")
    available = False
else:
    # On mac, hidapi has issues creating internal state in
    # multithreaded contexts. An extra call to enumerate 
    # apparently avoids this problem.
    hid.enumerate(0, 0)
    available = True

class HidApiUSB(Interface):
    """
    This class provides basic functions to access
    a USB HID device using cython-hidapi:
        - write/read an endpoint
    """
    name = 'hidapiusb'
    available = available

    def __init__(self):
        super(HidApiUSB, self).__init__()
        # Vendor page and usage_id = 2
        self.device = None

    def open(self):
        try:
            self.device.open(self.vid, self.pid)
        except AttributeError:
            pass

    @staticmethod
    def getConnectedInterfaces(vid, pid):
        """
        returns all the connected devices which matches HidApiUSB.vid/HidApiUSB.pid.
        returns an array of HidApiUSB (Interface) objects
        """

        devices = hid.enumerate(vid, pid)

        if not devices:
            logging.debug("No Mbed device connected")
            return

        boards = []

        for deviceInfo in devices:
            try:
                dev = hid.device(vendor_id=vid, product_id=pid, path = deviceInfo['path'])
            except IOError:
                logging.debug("Failed to open Mbed device")
                return

            # Create the USB interface object for this device.
            new_board = HidApiUSB()
            new_board.vendor_name = deviceInfo['manufacturer_string']
            new_board.product_name = deviceInfo['product_string']
            new_board.serial_number = deviceInfo['serial_number']
            new_board.vid = deviceInfo['vendor_id']
            new_board.pid = deviceInfo['product_id']
            new_board.path = deviceInfo['path']
            new_board.device = dev

            boards.append(new_board)

        return boards

    def write(self, data):
        """
        write data on the OUT endpoint associated to the HID interface
        """
        for _ in range(64 - len(data)):
            data.append(0)

        self.device.write([0] + data)
        return


    def read(self, timeout = -1):
        """
        read data on the IN endpoint associated to the HID interface
        """
        return self.device.read(64)

    def close(self):
        """
        close the interface
        """
        self.device.close()

    def setPacketCount(self, count):
        # No interface level restrictions on count
        self.packet_count = count

    def __eq__(self, other):
        return self.path == other.path
