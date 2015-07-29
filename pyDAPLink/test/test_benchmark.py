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
from random import randint
from time import time


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

@pytest.fixture
def write_data():
    """ Data to read/write """
    return [randint(0, 0xffffffff) for i in xrange(250)]

@pytest.fixture(scope='module')
def log(request):
    """ Logging after tests """
    data = []

    def log_append(first, *rest):
        data.append(('{:<15}' + len(rest)*'{:>15}').format(first, *rest))

    def log_print():
        print '\n', '\n'.join(data)

    request.addfinalizer(log_print)
    return log_append

def enable_debug(board):
    board.writeDP(DP_REG['SELECT'], 0)
    board.writeDP(DP_REG['CTRL_STAT'], CPWRUPREQ)
    while True:
        stat = board.readDP(DP_REG['CTRL_STAT'])
        assert isinstance(stat, int)
        if (stat & CPWRUPACK) == CPWRUPACK:
            break


class TestBenchmark:
    def test_dp_writes(self, vid, pid, frequency, write_data, log):
        client = DAPLink()
        client.init()

        boards = client.getConnectedBoards(vid, pid)
        board = boards[0]
        board.init(frequency)

        # write to DP
        start = time()

        for write in write_data:
            board.writeDP(DP_REG['CTRL_STAT'], write)

        stop = time()

        log("Writing DP",
            "%d MHz" % (frequency/1e6),
            "%d bytes" % (4*len(write_data)),
            "%.3f seconds" % (stop - start),
            "%.3f B/s" % ((4*len(write_data))/(stop - start)))

        board.uninit()
        client.uninit()

    def test_dp_reads(self, vid, pid, frequency, write_data, log):
        client = DAPLink()
        client.init()

        boards = client.getConnectedBoards(vid, pid)
        board = boards[0]
        board.init(frequency)

        # read from DP
        start = time()

        for write in write_data:
            board.readDP(DP_REG['CTRL_STAT'])

        stop = time()

        log("Reading DP",
            "%d MHz" % (frequency/1e6),
            "%d bytes" % (4*len(write_data)),
            "%.3f seconds" % (stop - start),
            "%.3f B/s" % ((4*len(write_data))/(stop - start)))

        board.uninit()
        client.uninit()
        
    def test_ap_writes(self, vid, pid, frequency, write_data, log):
        client = DAPLink()
        client.init()

        boards = client.getConnectedBoards(vid, pid)
        board = boards[0]
        board.init(frequency)

        enable_debug(board)

        # write to AP
        start = time()

        for write in write_data:
            board.writeAP(AP_REG['TAR'], write)

        stop = time()

        log("Writing AP",
            "%d MHz" % (frequency/1e6),
            "%d bytes" % (4*len(write_data)),
            "%.3f seconds" % (stop - start),
            "%.3f B/s" % ((4*len(write_data))/(stop - start)))

        board.uninit()
        client.uninit()

    def test_ap_reads(self, vid, pid, frequency, write_data, log):
        client = DAPLink()
        client.init()

        boards = client.getConnectedBoards(vid, pid)
        board = boards[0]
        board.init(frequency)

        enable_debug(board)

        # read from AP
        start = time()

        for write in write_data:
            board.readAP(AP_REG['TAR'])

        stop = time()

        log("Reading AP",
            "%d MHz" % (frequency/1e6),
            "%d bytes" % (4*len(write_data)),
            "%.3f seconds" % (stop - start),
            "%.3f B/s" % ((4*len(write_data))/(stop - start)))

        board.uninit()
        client.uninit()

    def test_mem_writes(self, vid, pid, frequency, write_data, log):
        client = DAPLink()
        client.init()

        boards = client.getConnectedBoards(vid, pid)
        board = boards[0]
        board.init(frequency)

        enable_debug(board)

        # write to memory
        start = time()

        for write in write_data:
            board.writeMem(DCRDR, write)

        stop = time()

        log("Writing memory",
            "%d MHz" % (frequency/1e6),
            "%d bytes" % (4*len(write_data)),
            "%.3f seconds" % (stop - start),
            "%.3f B/s" % ((4*len(write_data))/(stop - start)))

        board.uninit()
        client.uninit()

    def test_mem_reads(self, vid, pid, frequency, write_data, log):
        client = DAPLink()
        client.init()

        boards = client.getConnectedBoards(vid, pid)
        board = boards[0]
        board.init(frequency)

        enable_debug(board)

        # read from memory
        start = time()

        for write in write_data:
            board.readMem(DCRDR)

        stop = time()

        log("Reading memory",
            "%d MHz" % (frequency/1e6),
            "%d bytes" % (4*len(write_data)),
            "%.3f seconds" % (stop - start),
            "%.3f B/s" % ((4*len(write_data))/(stop - start)))

        board.uninit()
        client.uninit()

