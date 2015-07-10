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

from .protocol import CMSIS_DAP
from ..errors import TransferError
from ..interface import INTERFACE, usb_backend
import logging
from time import sleep

# !! This value are A[2:3] and not A[3:2]
DP_REG = {'IDCODE' : 0x00,
          'ABORT' : 0x00,
          'CTRL_STAT': 0x04,
          'SELECT': 0x08
          }

AP_REG = {'CSW' : 0x00,
          'TAR' : 0x04,
          'DRW' : 0x0C,
          'IDR' : 0xFC
          }

IDCODE = 0 << 2
AP_ACC = 1 << 0
DP_ACC = 0 << 0
READ = 1 << 1
WRITE = 0 << 1
VALUE_MATCH = 1 << 4
MATCH_MASK = 1 << 5

A32 = 0x0c
APSEL = 0xff000000
APBANKSEL = 0x000000f0

# AP Control and Status Word definitions
CSW_SIZE     =  0x00000007
CSW_SIZE8    =  0x00000000
CSW_SIZE16   =  0x00000001
CSW_SIZE32   =  0x00000002
CSW_ADDRINC  =  0x00000030
CSW_NADDRINC =  0x00000000
CSW_SADDRINC =  0x00000010
CSW_PADDRINC =  0x00000020
CSW_DBGSTAT  =  0x00000040
CSW_TINPROG  =  0x00000080
CSW_HPROT    =  0x02000000
CSW_MSTRTYPE =  0x20000000
CSW_MSTRCORE =  0x00000000
CSW_MSTRDBG  =  0x20000000
CSW_RESERVED =  0x01000000

CSW_VALUE  = (CSW_RESERVED | CSW_MSTRDBG | CSW_HPROT | CSW_DBGSTAT | CSW_SADDRINC)

TRANSFER_SIZE = {8: CSW_SIZE8,
                 16: CSW_SIZE16,
                 32: CSW_SIZE32
                 }

# Response values to DAP_Connect command
DAP_MODE_SWD = 1
DAP_MODE_JTAG = 2

# DP Control / Status Register bit definitions
CTRLSTAT_STICKYORUN = 0x00000002
CTRLSTAT_STICKYCMP = 0x00000010
CTRLSTAT_STICKYERR = 0x00000020

COMMANDS_PER_DAP_TRANSFER = 12


class DAPLinkCore(object):
    """
    This class implements the CMSIS-DAP protocol
    """
    def __init__(self, interface):
        self._protocol = CMSIS_DAP(interface)
        self._csw = -1
        self._dp_select = -1

        self._request_list = []
        self._data_list = []
        self._response_list = []
        self._handler_list = []

    def init(self, frequency = 1000000):
        # Flush to be safe
        self.flush()
        # connect to DAP, check for SWD or JTAG
        self.mode = self._protocol.connect()
        # set clock frequency
        self._protocol.setSWJClock(frequency)
        # configure transfer
        self._protocol.transferConfigure()

        if (self.mode == DAP_MODE_SWD):
            # configure swd protocol
            self._protocol.swdConfigure()
            # switch from jtag to swd
            self.JTAG2SWD()
            # read ID code
            self.readDP(DP_REG['IDCODE'])
            logging.info('IDCODE: 0x%X', self.flush())
            # clear errors
            self._protocol.writeAbort(0x1e);
        elif (self.mode == DAP_MODE_JTAG):
            # configure jtag protocol
            self._protocol.jtagConfigure(4)
            # Test logic reset, run test idle
            self._protocol.swjSequence([0x1F])
            # read ID code
            logging.info('IDCODE: 0x%X', self._protocol.jtagIDCode())
            # clear errors
            self.writeDP(DP_REG['CTRL_STAT'], CTRLSTAT_STICKYERR | CTRLSTAT_STICKYCMP | CTRLSTAT_STICKYORUN)
            self.flush()
        return

    def uninit(self):
        self.flush()
        self._protocol.disconnect()
        return

    def JTAG2SWD(self):
        data = [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff]
        self._protocol.swjSequence(data)

        data = [0x9e, 0xe7]
        self._protocol.swjSequence(data)

        data = [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff]
        self._protocol.swjSequence(data)

        data = [0x00]
        self._protocol.swjSequence(data)

    def clearStickyErr(self):
        if (self.mode == DAP_MODE_SWD):
            self.writeDP(0x0, (1 << 2))
        elif (self.mode == DAP_MODE_JTAG):
            self.writeDP(DP_REG['CTRL_STAT'], CTRLSTAT_STICKYERR)

    def info(self, request):
        self._flush()
        resp = None
        try:
            resp = self._protocol.dapInfo(request)
        except KeyError:
            logging.error('request %s not supported', request)
        return resp

    def writeDP(self, addr, data):
        if addr == DP_REG['SELECT']:
            if data == self._dp_select:
                return
            self._dp_select = data

        self._write(WRITE | DP_ACC | (addr & A32), data)

    def readDP(self, addr):
        self._write(READ | DP_ACC | (addr & A32))
        self._read(4, lambda resp: (resp[0] << 0)  |
                                   (resp[1] << 8)  |
                                   (resp[2] << 16) |
                                   (resp[3] << 24))

    def writeAP(self, addr, data):
        ap_sel = addr & APSEL
        bank_sel = addr & APBANKSEL
        self.writeDP(DP_REG['SELECT'], ap_sel | bank_sel) # TODO move this after check?

        if addr == AP_REG['CSW']:
            if data == self._csw:
                return
            self._csw = data

        self._write(WRITE | AP_ACC | (addr & A32), data)

    def readAP(self, addr):
        ap_sel = addr & APSEL
        bank_sel = addr & APBANKSEL

        self.writeDP(DP_REG['SELECT'], ap_sel | bank_sel)
        self._write(READ | AP_ACC | (addr & A32))

        self._read(4, lambda resp: (resp[0] << 0)  |
                                   (resp[1] << 8)  |
                                   (resp[2] << 16) |
                                   (resp[3] << 24))

    def writeMem(self, addr, data, transfer_size = 32):
        self.writeAP(AP_REG['CSW'], CSW_VALUE | TRANSFER_SIZE[transfer_size])

        if transfer_size == 8:
            data = data << ((addr & 0x03) << 3)
        elif transfer_size == 16:
            data = data << ((addr & 0x02) << 3)

        self._write(WRITE | AP_ACC | AP_REG['TAR'], addr)
        self._write(WRITE | AP_ACC | AP_REG['DRW'], data)

    def readMem(self, addr, transfer_size = 32):
        self.writeAP(AP_REG['CSW'], CSW_VALUE | TRANSFER_SIZE[transfer_size])
        self._write(WRITE | AP_ACC | AP_REG['TAR'], addr)
        self._write(READ | AP_ACC | AP_REG['DRW'])

        def handleResp(resp):
            res = ((resp[0] << 0)  |
                   (resp[1] << 8)  |
                   (resp[2] << 16) |
                   (resp[3] << 24))

            if transfer_size == 8:
                res = (res >> ((addr & 0x03) << 3) & 0xff)
            elif transfer_size == 16:
                res = (res >> ((addr & 0x02) << 3) & 0xffff)

            return res

        self._read(4, handleResp)

    # write aligned word ("data" are words)
    def writeBlock32(self, addr, data):
        # put address in TAR
        self.writeAP(AP_REG['CSW'], CSW_VALUE | CSW_SIZE32)
        self.writeAP(AP_REG['TAR'], addr)

        try:
            self._writeBlock(len(data), WRITE | AP_ACC | AP_REG['DRW'], data)
        except TransferError:
            self.clearStickyErr()
            raise

    # read aligned word (the size is in words)
    def readBlock32(self, addr, size):
        # put address in TAR
        self.writeAP(AP_REG['CSW'], CSW_VALUE | CSW_SIZE32)
        self.writeAP(AP_REG['TAR'], addr)

        try:
            self._writeBlock(size, READ | AP_ACC | AP_REG['DRW'])
            self._readBlock(4*size, lambda resp:
                    [(resp[i*4 + 0] << 0)  |
                     (resp[i*4 + 1] << 8)  |
                     (resp[i*4 + 2] << 16) |
                     (resp[i*4 + 3] << 24) 
                     for i in range(size)])
        except:
            self.clearStickyErr()
            raise

    def reset(self):
        self._flush()
        self._protocol.setSWJPins(0, 'nRESET')
        sleep(0.1)
        self._protocol.setSWJPins(0x80, 'nRESET')
        sleep(0.1)

    def assertReset(self, asserted):
        self._flush()
        if asserted:
            self._protocol.setSWJPins(0, 'nRESET')
        else:
            self._protocol.setSWJPins(0x80, 'nRESET')

    def setClock(self, frequency):
        self._flush()
        self._protocol.setSWJClock(frequency)

    def flush(self):
        """
        Flush out all commands and returns results from pending reads.
        """
        self._flush()

        index = 0
        results = []

        for count, handler in self._handler_list:
            res = handler(self._response_list[:count])
            self._response_list = self._response_list[count:]
            results.append(res)

        self._handler_list = []
        return results

    def _flush(self):
        """
        Flush out the transfer buffers but don't clear the response buffer.
        """
        transfer_count = len(self._request_list)

        if transfer_count > 0:
            assert transfer_count <= COMMANDS_PER_DAP_TRANSFER
            try:
                resp = self._protocol.transfer(
                        transfer_count, self._request_list, self._data_list)
                self._response_list.extend(resp)
            except TransferError:
                # Dump any pending commands
                self._request_list = []
                self._data_list = []
                self._handler_list = []
                # Dump any data read
                self._response_list = []
                # Invalidate cached registers
                self._csw = -1
                self._dp_select = -1
                # Clear error
                self.clearStickyErr()
                raise

            self._request_list = []
            self._data_list = []

    def _write(self, request, data = 0):
        """
        Write a single command
        """
        self._request_list.append(request)
        self._data_list.append(data)

        transfer_count = len(self._request_list)
        if (transfer_count >= COMMANDS_PER_DAP_TRANSFER):
            self._flush()

    def _read(self, count, handler):
        """
        Register a handler for the response from a single command
        """
        self._handler_list.append((count, handler))

    def _writeBlock(self, count, request, data = [0]):
        """
        Write a block
        """
        self._flush()
        res = self._protocol.transferBlock(count, request, data)
        self._response_list.extend(res)

    def _readBlock(self, count, handler):
        """
        Register a handler for a block
        """
        self._handler_list.append((count, handler))
