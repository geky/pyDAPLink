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
from pyDAPLink import DAPLinkServer
from pyDAPLink.socket import default_client
from pyDAPLink.utility import encode, decode

# Define address for tests to operate on
DP_REG = {'IDCODE':    0x00,
          'CTRL_STAT': 0x04,
          'SELECT':    0x08}

AP_REG = {'CSW': 0x00,
          'TAR': 0x04,
          'IDR': 0xFC}

MEM_ADDR = {'DCRDR': 0xE000EDF8}


@pytest.fixture(scope='function')
def server(request):
    """ Server for testing """
    server = DAPLinkServer()
    server.init()
    def cleanup():
        server.uninit()
    request.addfinalizer(cleanup)
    return server

@pytest.fixture(scope='function')
def socket(request, server):
    """ Socket connected to server for testing """
    socket = default_client()
    socket.init()
    def cleanup():
        socket.close()
    request.addfinalizer(cleanup)
    return socket

@pytest.fixture(scope='function')
def command(request, socket):
    """ Provides a command function for sending commands to a server """
    def command_func(command):
        assert isinstance(command, dict)

        socket.send(encode(command))
        response = decode(socket.recv())

        assert socket.isalive()
        assert isinstance(response, dict)
        assert 'error' not in response
        return response

    return command_func


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


def enable_debug(command):
    CPWRUPREQ = 0x50000000
    CPWRUPACK = 0xa0000000

    command({'command': 'write_dp', 'addr': DP_REG['SELECT'], 'data': 0})
    command({'command': 'write_dp', 'addr': DP_REG['CTRL_STAT'], 'data': CPWRUPREQ})
    command({'command': 'flush'})

    while True:
        command({'command': 'read_dp', 'addr': DP_REG['CTRL_STAT']})
        response = command({'command': 'flush'})
        if (response['reads'][0] & CPWRUPACK) == CPWRUPACK:
            break


class TestCommands:
    def test_server_info(self, command):
        response = command({'command': 'server_info'})

        assert 'response' in response and response['response'] == 'server_info'
        assert 'version' in response and isinstance(response['version'], basestring)


    def test_board_enumerate(self, command, vid, pid):
        response = command({'command': 'board_enumerate',
                            'vid': vid,
                            'pid': pid})

        assert 'response' in response and response['response'] == 'board_enumerate'
        assert 'ids' in response and isinstance(response['ids'], list)
        assert all(isinstance(id, int) for id in response['ids'])

    def test_board_select(self, command, vid, pid):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid}) 
        id = response['ids'][0]

        response = command({'command': 'board_select',
                            'id': id})

        assert 'response' in response and response['response'] == 'board_select'
        assert 'selected' in response and isinstance(response['selected'], bool)

    def test_board_deselect(self, command, vid, pid):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid}) 
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})

        response = command({'command': 'board_deselect'})

        assert 'response' in response and response['response'] == 'board_deselect'

    def test_board_info(self, command, vid, pid):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid}) 
        id = response['ids'][0]

        response = command({'command': 'board_info',
                            'id': id})

        assert 'response' in response and response['response'] == 'board_info'
        assert 'vendor'  in response and isinstance(response['vendor'],  basestring)
        assert 'product' in response and isinstance(response['product'], basestring)
        assert 'serial'  in response and isinstance(response['serial'],  basestring)


    def test_dap_init(self, command, vid, pid, frequency):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid}) 
        id = response['ids'][0] 
        command({'command': 'board_select', 'id': id})

        response = command({'command': 'dap_init',
                            'frequency': frequency})

        assert 'response' in response and response['response'] == 'dap_init'
        
    def test_dap_uninit(self, command, vid, pid, frequency):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid}) 
        id = response['ids'][0] 
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        response = command({'command': 'dap_uninit'})

        assert 'response' in response and response['response'] == 'dap_uninit'

    @pytest.mark.parametrize(('new_frequency',), [(10**6,), (10**7,), (10**8,)])
    def test_dap_clock(self, command, vid, pid, frequency, new_frequency):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid}) 
        id = response['ids'][0] 
        command({'command': 'board_select', 'id': id}) 
        command({'command': 'dap_init', 'frequency': frequency})

        response = command({'command': 'dap_clock',
                            'frequency': new_frequency})

        assert 'response' in response and response['response'] == 'dap_clock'

    @pytest.mark.parametrize(('info_request', 'info_type'), [
        ('VENDOR_ID',            basestring),
        ('PRODUCT_ID',           basestring),
        ('SERIAL_NUMBER',        basestring),
        ('CMSIS_DAP_FW_VERSION', basestring),
        ('TARGET_DEVICE_VENDOR', basestring),
        ('TARGET_DEVICE_NAME',   basestring),
        ('CAPABILITIES',         int),
        ('PACKET_COUNT',         int),
        ('PACKET_SIZE',          int)])
    def test_dap_info(self, command, vid, pid, frequency, info_request, info_type):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        response = command({'command': 'dap_info',
                            'request': info_request})

        assert 'response' in response and response['response'] == 'dap_info'
        assert 'result' in response
        assert response['result'] is None or isinstance(response['result'], info_type)
        

    def test_reset(self, command, vid, pid, frequency):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        response = command({'command': 'reset'})

        assert 'response' in response and response['response'] == 'reset'

    def test_reset_assert(self, command, vid, pid, frequency):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        response = command({'command': 'reset_assert'})
        assert 'response' in response and response['response'] == 'reset_assert'

        response = command({'command': 'reset_deassert'})
        assert 'response' in response and response['response'] == 'reset_deassert'


    def test_flush(self, command, vid, pid, frequency):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        response = command({'command': 'flush'})

        assert 'response' in response and response['response'] == 'flush'

    @pytest.mark.parametrize('reg', ['IDCODE', 'CTRL_STAT'])
    def test_read_dp(self, command, vid, pid, frequency, reg):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        response = command({'command': 'read_dp',
                            'addr': DP_REG[reg]})

        assert 'response' in response and response['response'] == 'read_dp'
        response = command({'command': 'flush'})
        assert 'response' in response and response['response'] == 'flush'
        assert 'reads' in response and isinstance(response['reads'], list)
        assert len(response['reads']) == 1
        assert all(isinstance(read, int) for read in response['reads'])

    @pytest.mark.parametrize('reg', ['SELECT', 'CTRL_STAT'])
    def test_write_dp(self, command, vid, pid, frequency, reg):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        response = command({'command': 'write_dp',
                            'addr': DP_REG[reg],
                            'data': 0})

        assert 'response' in response and response['response'] == 'write_dp'
        response = command({'command': 'flush'})
        assert 'response' in response and response['response'] == 'flush'
        
    @pytest.mark.parametrize('reg', ['CSW', 'IDR'])
    def test_read_ap(self, command, vid, pid, frequency, reg):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        enable_debug(command)

        response = command({'command': 'read_ap',
                            'addr': AP_REG[reg]})

        assert 'response' in response and response['response'] == 'read_ap'
        response = command({'command': 'flush'})
        assert 'response' in response and response['response'] == 'flush'
        assert 'reads' in response and isinstance(response['reads'], list)
        assert len(response['reads']) == 1 and isinstance(response['reads'][0], int)
        assert all(isinstance(read, int) for read in response['reads'])

    @pytest.mark.parametrize('reg', ['CSW', 'TAR'])
    def test_write_ap(self, command, vid, pid, frequency, reg):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        enable_debug(command)

        response = command({'command': 'write_ap',
                            'addr': AP_REG[reg],
                            'data': 0})

        assert 'response' in response and response['response'] == 'write_ap'
        response = command({'command': 'flush'})
        assert 'response' in response and response['response'] == 'flush'

    @pytest.mark.parametrize(('address', 'size'), [
        ('DCRDR', 8), 
        ('DCRDR', 16), 
        ('DCRDR', 32)])
    def test_read_mem(self, command, vid, pid, frequency, address, size):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        enable_debug(command)

        for offset in range(0, 4, size/8):
            response = command({'command': 'read_%d' % size,
                                'addr': MEM_ADDR[address]+offset})

        assert 'response' in response and response['response'] == 'read_%d' % size
        response = command({'command': 'flush'})
        assert 'response' in response and response['response'] == 'flush'
        assert 'reads' in response and isinstance(response['reads'], list)
        assert len(response['reads']) == 32/size
        assert all(isinstance(read, int) for read in response['reads'])

    @pytest.mark.parametrize(('address', 'size'), [
        ('DCRDR', 8),
        ('DCRDR', 16),
        ('DCRDR', 32)])
    def test_write_mem(self, command, vid, pid, frequency, address, size):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        enable_debug(command)

        for offset in range(0, 4, size/8):
            response = command({'command': 'write_%d' % size,
                                'addr': MEM_ADDR[address]+offset,
                                'data': 0})

        assert 'response' in response and response['response'] == 'write_%d' % size
        response = command({'command': 'flush'})
        assert 'response' in response and response['response'] == 'flush'

    @pytest.mark.parametrize(('address', 'count'), [('DCRDR', 1)])
    def test_read_block(self, command, vid, pid, frequency, address, count):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        enable_debug(command)

        response = command({'command': 'read_block',
                            'addr': MEM_ADDR[address],
                            'count': count})

        assert 'response' in response and response['response'] == 'read_block'
        response = command({'command': 'flush'})
        assert 'response' in response and response['response'] == 'flush'
        assert 'reads' in response and isinstance(response['reads'], list)
        assert len(response['reads']) == 1
        assert all(isinstance(read, list) for read in response['reads'])
        assert all(isinstance(word, int) for read in response['reads'] 
                                         for word in read)

    @pytest.mark.parametrize(('address', 'count'), [('DCRDR', 1)])
    def test_write_block(self, command, vid, pid, frequency, address, count):
        response = command({'command': 'board_enumerate', 'vid': vid, 'pid': pid})
        id = response['ids'][0]
        command({'command': 'board_select', 'id': id})
        command({'command': 'dap_init', 'frequency': frequency})

        enable_debug(command)

        response = command({'command': 'write_block',
                            'addr': MEM_ADDR[address],
                            'data': [0]*count})

        assert 'response' in response and response['response'] == 'write_block'
        response = command({'command': 'flush'})
        assert 'response' in response and response['response'] == 'flush'
