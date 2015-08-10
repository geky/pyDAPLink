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
    import pywinusb.hid as hid
except:
    if os.name == "nt":
        logging.error("PyWinUSB is required on a Windows Machine")
    available = False
else:
    available = True

class PyWinUSB(Interface):
    """
    This class provides basic functions to access
    a USB HID device using pywinusb:
        - write/read an endpoint
    """
    name = 'pywinusb'
    available = available
    
    def __init__(self):
        super(PyWinUSB, self).__init__()
        # Vendor page and usage_id = 2
        self.report = []
        self.rcv_data = []
        self.device = None
        return
    
    # handler called when a report is received
    def rx_handler(self, data):
        #logging.debug("rcv: %s", data[1:])
        self.rcv_data.append(data[1:])
    
    def open(self):
        self.device.open()

	reports = self.device.find_output_reports()
        if len(reports) != 1:
            raise ValueError('Unexpected USB reports')
        self.report = reports[0]

        self.device.set_raw_data_handler(self.rx_handler)
        
    @staticmethod
    def getConnectedInterfaces(vid, pid):
        """
        returns all the connected devices which matches PyWinUSB.vid/PyWinUSB.pid.
        returns an array of PyWinUSB (Interface) objects
        """
        all_devices = hid.find_all_hid_devices()
        
        # find devices with good vid/pid
        all_mbed_devices = []
        for d in all_devices:
            if (d.vendor_id == vid) and (d.product_id == pid):
                all_mbed_devices.append(d)
                
        if not all_mbed_devices:
            logging.debug("No Mbed device connected")
            return
            
        boards = []
        for dev in all_mbed_devices:
            new_board = PyWinUSB()
            new_board.vendor_name = dev.vendor_name
            new_board.product_name = dev.product_name
            new_board.serial_number = dev.serial_number
            new_board.vid = dev.vendor_id
            new_board.pid = dev.product_id
            new_board.path = dev.device_path
            new_board.device = dev

            boards.append(new_board)
                
        return boards
    
    def write(self, data):
        """
        write data on the OUT endpoint associated to the HID interface
        """
        for _ in range(64 - len(data)):
            data.append(0)
        #logging.debug("send: %s", data)
        self.report.send([0] + data)
        return
        
        
    def read(self, timeout = -1):
        """
        read data on the IN endpoint associated to the HID interface
        """
        while len(self.rcv_data) == 0:
            pass
        return self.rcv_data.pop(0)

    def setPacketCount(self, count):
        # No interface level restrictions on count
        self.packet_count = count

    def __eq__(self, other):
        return self.path == other.path

    def close(self):
        """
        close the interface
        """
        logging.debug("closing interface")
        self.device.close()
