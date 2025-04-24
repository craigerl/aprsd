import datetime
import socket
import unittest
from unittest import mock

import aprslib

from aprsd import exception
from aprsd.client.drivers.registry import ClientDriver
from aprsd.client.drivers.tcpkiss import TCPKISSDriver
from aprsd.packets import core


class TestTCPKISSDriver(unittest.TestCase):
    """Unit tests for the TCPKISSDriver class."""

    def setUp(self):
        # Mock configuration
        self.conf_patcher = mock.patch('aprsd.client.drivers.tcpkiss.CONF')
        self.mock_conf = self.conf_patcher.start()

        # Configure KISS settings
        self.mock_conf.kiss_tcp.enabled = True
        self.mock_conf.kiss_tcp.host = '127.0.0.1'
        self.mock_conf.kiss_tcp.port = 8001
        self.mock_conf.kiss_tcp.path = ['WIDE1-1', 'WIDE2-1']

        # Mock socket
        self.socket_patcher = mock.patch('aprsd.client.drivers.tcpkiss.socket')
        self.mock_socket_module = self.socket_patcher.start()
        self.mock_socket = mock.MagicMock()
        self.mock_socket_module.socket.return_value = self.mock_socket

        # Mock select
        self.select_patcher = mock.patch('aprsd.client.drivers.tcpkiss.select')
        self.mock_select = self.select_patcher.start()

        # Create an instance of the driver
        self.driver = TCPKISSDriver()

    def tearDown(self):
        self.conf_patcher.stop()
        self.socket_patcher.stop()
        self.select_patcher.stop()

    def test_implements_client_driver_protocol(self):
        """Test that TCPKISSDriver implements the ClientDriver Protocol."""
        # Verify the instance is recognized as implementing the Protocol
        self.assertIsInstance(self.driver, ClientDriver)

        # Verify all required methods are present with correct signatures
        required_methods = [
            'is_enabled',
            'is_configured',
            'is_alive',
            'close',
            'send',
            'setup_connection',
            'set_filter',
            'login_success',
            'login_failure',
            'consumer',
            'decode_packet',
            'stats',
        ]

        for method_name in required_methods:
            self.assertTrue(
                hasattr(self.driver, method_name),
                f'Missing required method: {method_name}',
            )

    def test_init(self):
        """Test initialization sets default values."""
        self.assertFalse(self.driver._connected)
        self.assertIsInstance(self.driver.keepalive, datetime.datetime)
        self.assertFalse(self.driver._running)

    def test_transport_property(self):
        """Test transport property returns correct value."""
        self.assertEqual(self.driver.transport, 'tcpkiss')

    def test_is_enabled_true(self):
        """Test is_enabled returns True when KISS TCP is enabled."""
        self.mock_conf.kiss_tcp.enabled = True
        self.assertTrue(TCPKISSDriver.is_enabled())

    def test_is_enabled_false(self):
        """Test is_enabled returns False when KISS TCP is disabled."""
        self.mock_conf.kiss_tcp.enabled = False
        self.assertFalse(TCPKISSDriver.is_enabled())

    def test_is_configured_true(self):
        """Test is_configured returns True when properly configured."""
        with mock.patch.object(TCPKISSDriver, 'is_enabled', return_value=True):
            self.mock_conf.kiss_tcp.host = '127.0.0.1'
            self.assertTrue(TCPKISSDriver.is_configured())

    def test_is_configured_false_no_host(self):
        """Test is_configured returns False when host not set."""
        with mock.patch.object(TCPKISSDriver, 'is_enabled', return_value=True):
            self.mock_conf.kiss_tcp.host = None
            with self.assertRaises(exception.MissingConfigOptionException):
                TCPKISSDriver.is_configured()

    def test_is_configured_false_not_enabled(self):
        """Test is_configured returns False when not enabled."""
        with mock.patch.object(TCPKISSDriver, 'is_enabled', return_value=False):
            self.assertFalse(TCPKISSDriver.is_configured())

    def test_is_alive(self):
        """Test is_alive property returns connection state."""
        self.driver._connected = True
        self.assertTrue(self.driver.is_alive)

        self.driver._connected = False
        self.assertFalse(self.driver.is_alive)

    def test_close(self):
        """Test close method calls stop."""
        with mock.patch.object(self.driver, 'stop') as mock_stop:
            self.driver.close()
            mock_stop.assert_called_once()

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_setup_connection_success(self, mock_log):
        """Test setup_connection successfully connects."""
        # Mock the connect method to succeed
        is_en = self.driver.is_enabled
        is_con = self.driver.is_configured
        self.driver.is_enabled = mock.MagicMock(return_value=True)
        self.driver.is_configured = mock.MagicMock(return_value=True)
        with mock.patch.object(
            self.driver, 'connect', return_value=True
        ) as mock_connect:
            self.driver.setup_connection()
            mock_connect.assert_called_once()
            mock_log.info.assert_called_with('KISS TCP Connection to 127.0.0.1:8001')

        self.driver.is_enabled = is_en
        self.driver.is_configured = is_con

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_setup_connection_failure(self, mock_log):
        """Test setup_connection handles connection failure."""
        # Mock the connect method to fail
        with mock.patch.object(
            self.driver, 'connect', return_value=False
        ) as mock_connect:
            self.driver.setup_connection()
            mock_connect.assert_called_once()
            mock_log.error.assert_called_with('Failed to connect to KISS interface')

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_setup_connection_exception(self, mock_log):
        """Test setup_connection handles exceptions."""
        # Mock the connect method to raise an exception
        with mock.patch.object(
            self.driver, 'connect', side_effect=Exception('Test error')
        ) as mock_connect:
            self.driver.setup_connection()
            mock_connect.assert_called_once()
            mock_log.error.assert_any_call('Failed to initialize KISS interface')
            mock_log.exception.assert_called_once()
            self.assertFalse(self.driver._connected)

    def test_set_filter(self):
        """Test set_filter does nothing for KISS."""
        # Just ensure it doesn't fail
        self.driver.set_filter('test/filter')

    def test_login_success_when_connected(self):
        """Test login_success returns True when connected."""
        self.driver._connected = True
        self.assertTrue(self.driver.login_success())

    def test_login_success_when_not_connected(self):
        """Test login_success returns False when not connected."""
        self.driver._connected = False
        self.assertFalse(self.driver.login_success())

    def test_login_failure(self):
        """Test login_failure returns success message."""
        self.assertEqual(self.driver.login_failure(), 'Login successful')

    @mock.patch('aprsd.client.drivers.tcpkiss.ax25frame.Frame.ui')
    def test_send_packet(self, mock_frame_ui):
        """Test sending an APRS packet."""
        # Create a mock frame
        mock_frame = mock.MagicMock()
        mock_frame_bytes = b'mock_frame_data'
        mock_frame.__bytes__ = mock.MagicMock(return_value=mock_frame_bytes)
        mock_frame_ui.return_value = mock_frame

        # Set up the driver
        self.driver.socket = self.mock_socket
        self.driver.path = ['WIDE1-1', 'WIDE2-1']

        # Create a mock packet
        mock_packet = mock.MagicMock(spec=core.Packet)
        mock_bytes = b'Test packet data'
        mock_packet.__bytes__ = mock.MagicMock(return_value=mock_bytes)
        # Add path attribute to the mock packet
        mock_packet.path = None

        # Send the packet
        self.driver.send(mock_packet)

        # Check that frame was created correctly
        mock_frame_ui.assert_called_once_with(
            destination='APZ100',
            source=mock_packet.from_call,
            path=self.driver.path,
            info=mock_packet.payload.encode('US-ASCII'),
        )

        # Check that socket send was called
        self.mock_socket.send.assert_called_once()

        # Verify packet counters updated
        self.assertEqual(self.driver.packets_sent, 1)
        self.assertIsNotNone(self.driver.last_packet_sent)

    def test_send_with_no_socket(self):
        """Test send raises exception when socket not initialized."""
        self.driver.socket = None
        mock_packet = mock.MagicMock(spec=core.Packet)

        with self.assertRaises(Exception) as context:
            self.driver.send(mock_packet)
        self.assertIn('KISS interface not initialized', str(context.exception))

    def test_stop(self):
        """Test stop method cleans up properly."""
        self.driver._running = True
        self.driver._connected = True
        self.driver.socket = self.mock_socket

        self.driver.stop()

        self.assertFalse(self.driver._running)
        self.assertFalse(self.driver._connected)
        self.mock_socket.close.assert_called_once()

    def test_stats(self):
        """Test stats method returns correct data."""
        # Set up test data
        self.driver._connected = True
        self.driver.path = ['WIDE1-1', 'WIDE2-1']
        self.driver.packets_sent = 5
        self.driver.packets_received = 3
        self.driver.last_packet_sent = datetime.datetime.now()
        self.driver.last_packet_received = datetime.datetime.now()

        # Get stats
        stats = self.driver.stats()

        # Check stats contains expected keys
        expected_keys = [
            'client',
            'transport',
            'connected',
            'path',
            'packets_sent',
            'packets_received',
            'last_packet_sent',
            'last_packet_received',
            'connection_keepalive',
            'host',
            'port',
        ]
        for key in expected_keys:
            self.assertIn(key, stats)

        # Check some specific values
        self.assertEqual(stats['client'], 'TCPKISSDriver')
        self.assertEqual(stats['transport'], 'tcpkiss')
        self.assertEqual(stats['connected'], True)
        self.assertEqual(stats['packets_sent'], 5)
        self.assertEqual(stats['packets_received'], 3)

    def test_stats_serializable(self):
        """Test stats with serializable=True converts datetime to ISO format."""
        self.driver.keepalive = datetime.datetime.now()

        stats = self.driver.stats(serializable=True)

        # Check keepalive is a string in ISO format
        self.assertIsInstance(stats['connection_keepalive'], str)
        # Try parsing it to verify it's a valid ISO format
        try:
            datetime.datetime.fromisoformat(stats['connection_keepalive'])
        except ValueError:
            self.fail('keepalive is not in valid ISO format')

    def test_connect_success(self):
        """Test successful connection."""
        result = self.driver.connect()

        self.assertTrue(result)
        self.assertTrue(self.driver._connected)
        self.mock_socket.connect.assert_called_once_with(
            (self.mock_conf.kiss_tcp.host, self.mock_conf.kiss_tcp.port)
        )
        self.mock_socket.settimeout.assert_any_call(5.0)
        self.mock_socket.settimeout.assert_any_call(0.1)

    def test_connect_failure_socket_error(self):
        """Test connection failure due to socket error."""
        self.mock_socket.connect.side_effect = socket.error('Test socket error')

        result = self.driver.connect()

        self.assertFalse(result)
        self.assertFalse(self.driver._connected)

    def test_connect_failure_timeout(self):
        """Test connection failure due to timeout."""
        self.mock_socket.connect.side_effect = socket.timeout('Test timeout')

        result = self.driver.connect()

        self.assertFalse(result)
        self.assertFalse(self.driver._connected)

    def test_fix_raw_frame(self):
        """Test fix_raw_frame removes KISS markers and handles FEND."""
        # Create a test frame with KISS markers
        with mock.patch(
            'aprsd.client.drivers.tcpkiss.handle_fend', return_value=b'fixed_frame'
        ) as mock_handle_fend:
            raw_frame = b'\xc0\x00some_frame_data\xc0'  # \xc0 is FEND

            result = self.driver.fix_raw_frame(raw_frame)

            mock_handle_fend.assert_called_once_with(b'some_frame_data')
            self.assertEqual(result, b'fixed_frame')

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_decode_packet_success(self, mock_log):
        """Test successful packet decoding."""
        mock_frame = 'test frame data'
        mock_aprs_data = {'from': 'TEST-1', 'to': 'APRS'}
        mock_packet = mock.MagicMock(spec=core.Packet)

        with mock.patch(
            'aprsd.client.drivers.tcpkiss.aprslib.parse', return_value=mock_aprs_data
        ) as mock_parse:
            with mock.patch(
                'aprsd.client.drivers.tcpkiss.core.factory', return_value=mock_packet
            ) as mock_factory:
                result = self.driver.decode_packet(frame=mock_frame)

                mock_parse.assert_called_once_with(str(mock_frame))
                mock_factory.assert_called_once_with(mock_aprs_data)
                self.assertEqual(result, mock_packet)

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_decode_packet_no_frame(self, mock_log):
        """Test decode_packet with no frame returns None."""
        result = self.driver.decode_packet()

        self.assertIsNone(result)
        mock_log.warning.assert_called_once()

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_decode_packet_exception(self, mock_log):
        """Test decode_packet handles exceptions."""
        mock_frame = 'invalid frame'

        with mock.patch(
            'aprsd.client.drivers.tcpkiss.aprslib.parse',
            side_effect=Exception('Test error'),
        ) as mock_parse:
            result = self.driver.decode_packet(frame=mock_frame)

            mock_parse.assert_called_once()
            self.assertIsNone(result)
            mock_log.error.assert_called_once()

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_consumer_with_frame(self, mock_log):
        """Test consumer processes frames and calls callback."""
        mock_callback = mock.MagicMock()
        mock_frame = mock.MagicMock()

        # Configure driver for test
        self.driver._connected = True
        self.driver._running = True

        # Set up read_frame to return one frame then stop
        def side_effect():
            self.driver._running = False
            return mock_frame

        with mock.patch.object(
            self.driver, 'read_frame', side_effect=side_effect
        ) as mock_read_frame:
            self.driver.consumer(mock_callback)

            mock_read_frame.assert_called_once()
            mock_callback.assert_called_once_with(frame=mock_frame)

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_consumer_with_connect_reconnect(self, mock_log):
        """Test consumer tries to reconnect when not connected."""
        mock_callback = mock.MagicMock()

        # Configure driver for test
        self.driver._connected = False

        # Setup to run once then stop
        call_count = 0

        def connect_side_effect():
            nonlocal call_count
            call_count += 1
            # On second call, connect successfully
            if call_count == 2:
                self.driver._running = False
                self.driver.socket = self.mock_socket
                return True
            return False

        with mock.patch.object(
            self.driver, 'connect', side_effect=connect_side_effect
        ) as mock_connect:
            with mock.patch('aprsd.client.drivers.tcpkiss.time.sleep') as mock_sleep:
                self.driver.consumer(mock_callback)

                self.assertEqual(mock_connect.call_count, 2)
                mock_sleep.assert_called_once_with(1)

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_read_frame_success(self, mock_log):
        """Test read_frame successfully reads a frame."""
        # Set up driver
        self.driver.socket = self.mock_socket
        self.driver._running = True

        # Mock socket recv to return data
        raw_data = b'\xc0\x00test_frame\xc0'
        self.mock_socket.recv.return_value = raw_data

        # Mock select to indicate socket is readable
        self.mock_select.select.return_value = ([self.mock_socket], [], [])

        # Mock fix_raw_frame and Frame.from_bytes
        mock_fixed_frame = b'fixed_frame'
        mock_ax25_frame = mock.MagicMock()

        with mock.patch.object(
            self.driver, 'fix_raw_frame', return_value=mock_fixed_frame
        ) as mock_fix:
            with mock.patch(
                'aprsd.client.drivers.tcpkiss.ax25frame.Frame.from_bytes',
                return_value=mock_ax25_frame,
            ) as mock_from_bytes:
                result = self.driver.read_frame()

                self.mock_socket.setblocking.assert_called_once_with(0)
                self.mock_select.select.assert_called_once()
                self.mock_socket.recv.assert_called_once()
                mock_fix.assert_called_once_with(raw_data)
                mock_from_bytes.assert_called_once_with(mock_fixed_frame)
                self.assertEqual(result, mock_ax25_frame)

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_read_frame_select_timeout(self, mock_log):
        """Test read_frame handles select timeout."""
        # Set up driver
        self.driver.socket = self.mock_socket
        self.driver._running = True

        # Mock select to indicate no readable sockets
        self.mock_select.select.return_value = ([], [], [])

        result = self.driver.read_frame()

        self.assertIsNone(result)

    @mock.patch('aprsd.client.drivers.tcpkiss.LOG')
    def test_read_frame_socket_error(self, mock_log):
        """Test read_frame handles socket error."""
        # Set up driver
        self.driver.socket = self.mock_socket
        self.driver._running = True

        # Mock setblocking to raise OSError
        self.mock_socket.setblocking.side_effect = OSError('Test error')

        with self.assertRaises(aprslib.ConnectionDrop):
            self.driver.read_frame()
            mock_log.error.assert_called_once()


if __name__ == '__main__':
    unittest.main()
