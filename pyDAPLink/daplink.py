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

from cmsis_dap import CMSIS_DAP, READ_START, READ_NOW, READ_END
from interface import INTERFACE, usb_backend
import logging
from time import sleep


class DAPLink(object):
    """
    This class implements the CMSIS-DAP protocol
    """
    def __init__(self, interface, frequency = 1000000):
        self.dap = CMSIS_DAP(interface)

    @staticmethod
    def getAllInterfaces(vid, pid):
        return INTERFACE[usb_backend].getAllConnectedInterface(vid, pid)

    def init(self, frequency):
        return self.dap.init(frequency)

    def uninit(self):
        return self.dap.uninit()

    def info(self, request):
        return self.dap.info(request)

    def readDP(self, addr, mode=READ_NOW):
        return self.dap.readDP(addr, mode)

    def writeDP(self, addr, data):
        return self.dap.writeDP(addr, data)

    def readAP(self, addr, mode=READ_NOW):
        return self.dap.readAP(addr, mode)

    def writeAP(self, addr, data):
        return self.dap.writeAP(addr, data)

    def readMem(self, addr, transfer_size=32, mode=READ_NOW):
        return self.dap.readMem(addr, transfer_size, mode)

    def writeMem(self, addr, data, transfer_size=32):
        return self.dap.writeMem(addr, data, transfer_size)

    def readBlock32(self, addr, data):
        return self.dap.readBlock32(addr, data)

    def writeBlock32(self, addr, data):
        return self.dap.writeBlock32(addr, data)

    def reset(self):
        return self.dap.reset()

    def assertReset(self, asserted):
        return self.dap.assertReset(asserted)

    def getUniqueID(self):
        return self.dap.getUniqueID()

    def setClock(self, frequency):
        return self.dap.setClock(frequency)

    def setDeferredTransfer(self, enable):
        return self.dap.setDeferredTransfer(enable)

    def flush(self):
        return self.dap.flush()
