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

import pytest
from pyDAPLink import DAPLink
from pyDAPLink import READ_START, READ_END
from pyDAPLink.daplink import DP_REG, AP_REG
from pyDAPLink.socket import SOCKET
from pyDAPLink.interface import INTERFACE
from numbers import Integral
from random import randint


# Some board definitions specific to Cortex-M parts for tests.
CPWRUPREQ = 0x50000000
CPWRUPACK = 0xa0000000
DCRDR = 0xE000EDF8


@pytest.fixture
def vid():
    """ VID of device for testing """
    return 0x0d28

@pytest.fixture
def pid():
    """ PID of device for testing """
    return 0x0204

@pytest.fixture(params=[10**6, 10**7, 10**8])
def frequency(request):
    """ Frequency for daplink connection """
    return request.param

@pytest.fixture(params=[1, 3, 5])
def packet_count(request):
    """ Packet count for daplink connection """
    return request.param

@pytest.fixture
def write_data():
    """ Data to read/write """
    return [randint(0, 0xffffffff) for i in xrange(25)]

@pytest.fixture(params=['normal', 'block', 'deferred'])
def access_type(request):
    """ Mode of transfer to test """
    return request.param


class TestClients:
    def test_basic_client(self, vid, pid, frequency, packet_count, access_type, write_data):
        client = DAPLink()
        client.init()

        boards = client.getConnectedBoards(vid, pid)
        for board in boards:
            assert (board.vid, board.pid) == (vid, pid)
            assert hasattr(board, 'vendor_name')   and isinstance(board.vendor_name,   basestring)
            assert hasattr(board, 'product_name')  and isinstance(board.product_name,  basestring)
            assert hasattr(board, 'serial_number') and isinstance(board.serial_number, basestring)

        board = boards[0]
        board.init(frequency, packet_count)
        assert board.locked

        if access_type == 'deferred':
            board.setDeferredTransfer(True)

        board.reset()

        # power up debug unit
        board.writeDP(DP_REG['SELECT'], 0)
        board.writeDP(DP_REG['CTRL_STAT'], CPWRUPREQ)
        while True:
            stat = board.readDP(DP_REG['CTRL_STAT'])
            assert isinstance(stat, Integral)
            if (stat & CPWRUPACK) == CPWRUPACK:
                break

        # write/read random data
        read_data = []

        if access_type == 'deferred':
            for write in write_data:
                board.writeMem(DCRDR, write)
                board.readMem(DCRDR, 32, READ_START)

            for write in write_data:
                read = board.readMem(DCRDR, 32, READ_END)
                read_data.append(read)
        elif access_type == 'block':
            for write in write_data:
                board.writeBlock32(DCRDR, [write])
                read = board.readBlock32(DCRDR, 1)
                assert isinstance(read, list)
                read_data.extend(read)
        else:
            for write in write_data:
                board.writeMem(DCRDR, write)
                read = board.readMem(DCRDR)
                read_data.append(read)

        assert all(isinstance(read, Integral) for read in read_data)
        assert read_data == write_data

        board.uninit()
        client.uninit()


        
