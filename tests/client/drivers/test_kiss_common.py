import datetime
import unittest
from unittest import mock

from aprsd.client.drivers.kiss_common import KISSDriver
from tests import fake


class ConcreteKISSDriver(KISSDriver):
    """Concrete implementation of KISSDriver for testing."""

    def __init__(self):
        super().__init__()
        self.path = '/dev/test'

    @staticmethod
    def transport() -> str:
        """Return transport type."""
        return 'test'

    def read_frame(self):
        """Implementation of abstract method."""
        return None


class TestKISSDriver(unittest.TestCase):
    """Unit tests for the KISSDriver class."""

    def setUp(self):
        """Set up test fixtures."""
        self.driver = ConcreteKISSDriver()

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_init(self):
        """Test initialization."""
        self.assertFalse(self.driver._connected)
        self.assertIsInstance(self.driver.keepalive, datetime.datetime)
        self.assertEqual(self.driver.select_timeout, 1)
        self.assertEqual(self.driver.packets_received, 0)
        self.assertEqual(self.driver.packets_sent, 0)

    def test_login_success_not_connected(self):
        """Test login_success() when not connected."""
        self.driver._connected = False
        self.assertFalse(self.driver.login_success())

    def test_login_success_connected(self):
        """Test login_success() when connected."""
        self.driver._connected = True
        self.assertTrue(self.driver.login_success())

    def test_login_failure(self):
        """Test login_failure() method."""
        result = self.driver.login_failure()
        self.assertEqual(result, 'Login successful')

    def test_set_filter(self):
        """Test set_filter() method."""
        # Should not raise exception (no-op for KISS)
        self.driver.set_filter('test filter')

    def test_filter_property(self):
        """Test filter property."""
        result = self.driver.filter
        self.assertEqual(result, '')

    def test_is_alive_not_connected(self):
        """Test is_alive property when not connected."""
        self.driver._connected = False
        self.assertFalse(self.driver.is_alive)

    def test_is_alive_connected(self):
        """Test is_alive property when connected."""
        self.driver._connected = True
        self.assertTrue(self.driver.is_alive)

    def test_handle_fend(self):
        """Test _handle_fend() method."""
        from kiss import util as kissutil

        buffer = b'\x00test_data'
        with mock.patch.object(kissutil, 'recover_special_codes') as mock_recover:
            with mock.patch.object(kissutil, 'strip_nmea') as mock_strip:
                with mock.patch.object(kissutil, 'strip_df_start') as mock_strip_df:
                    mock_strip.return_value = buffer
                    mock_recover.return_value = buffer
                    mock_strip_df.return_value = b'test_data'

                    result = self.driver._handle_fend(buffer, strip_df_start=True)
                    self.assertIsInstance(result, bytes)

    def test_fix_raw_frame(self):
        """Test fix_raw_frame() method."""
        raw_frame = b'\xc0\x00test_data\xc0'

        with mock.patch.object(self.driver, '_handle_fend') as mock_handle:
            mock_handle.return_value = b'fixed_frame'
            result = self.driver.fix_raw_frame(raw_frame)
            self.assertEqual(result, b'fixed_frame')
            # Should call _handle_fend with ax25_data (without KISS markers)
            mock_handle.assert_called()

    def test_decode_packet(self):
        """Test decode_packet() method."""
        frame = b'test_frame'
        mock_aprs_data = {'from': 'TEST', 'to': 'APRS'}
        mock_packet = fake.fake_packet()

        with mock.patch('aprsd.client.drivers.kiss_common.aprslib.parse') as mock_parse:
            with mock.patch(
                'aprsd.client.drivers.kiss_common.core.factory'
            ) as mock_factory:
                mock_parse.return_value = mock_aprs_data
                mock_factory.return_value = mock_packet

                result = self.driver.decode_packet(frame)
                self.assertEqual(result, mock_packet)
                mock_parse.assert_called_with(str(frame))

    def test_decode_packet_no_frame(self):
        """Test decode_packet() with no frame."""
        with mock.patch('aprsd.client.drivers.kiss_common.LOG') as mock_log:
            result = self.driver.decode_packet()
            self.assertIsNone(result)
            mock_log.warning.assert_called()

    def test_decode_packet_exception(self):
        """Test decode_packet() with exception."""
        frame = b'test_frame'

        with mock.patch('aprsd.client.drivers.kiss_common.aprslib.parse') as mock_parse:
            mock_parse.side_effect = Exception('Parse error')

            with mock.patch('aprsd.client.drivers.kiss_common.LOG') as mock_log:
                result = self.driver.decode_packet(frame)
                self.assertIsNone(result)
                mock_log.error.assert_called()

    def test_decode_packet_third_party(self):
        """Test decode_packet() with ThirdPartyPacket."""
        from aprsd.packets import core

        frame = b'test_frame'
        mock_aprs_data = {'from': 'TEST', 'to': 'APRS'}

        # Create a ThirdPartyPacket
        third_party = core.ThirdPartyPacket(
            from_call='TEST', to_call='APRS', subpacket=fake.fake_packet()
        )

        with mock.patch('aprsd.client.drivers.kiss_common.aprslib.parse') as mock_parse:
            with mock.patch(
                'aprsd.client.drivers.kiss_common.core.factory'
            ) as mock_factory:
                mock_parse.return_value = mock_aprs_data
                mock_factory.return_value = third_party

                result = self.driver.decode_packet(frame)
                self.assertEqual(result, third_party.subpacket)

    def test_consumer_not_connected(self):
        """Test consumer() when not connected."""
        self.driver._connected = False
        callback = mock.MagicMock()

        result = self.driver.consumer(callback)
        self.assertIsNone(result)
        callback.assert_not_called()

    def test_consumer_connected(self):
        """Test consumer() when connected."""
        self.driver._connected = True
        callback = mock.MagicMock()
        mock_frame = b'test_frame'
        mock_packet = mock.MagicMock()

        with mock.patch.object(self.driver, 'read_frame', return_value=mock_frame):
            with mock.patch.object(
                self.driver, 'decode_packet', return_value=mock_packet
            ):
                with mock.patch('aprsd.client.drivers.kiss_common.LOG'):
                    self.driver.consumer(callback)
                    callback.assert_called_once_with(packet=mock_packet)

    def test_read_frame_not_implemented(self):
        """Test read_frame() raises NotImplementedError."""
        driver = KISSDriver()
        with self.assertRaises(NotImplementedError):
            driver.read_frame()

    def test_stats(self):
        """Test stats() method."""
        self.driver._connected = True
        self.driver.packets_sent = 5
        self.driver.packets_received = 10
        self.driver.last_packet_sent = datetime.datetime.now()
        self.driver.last_packet_received = datetime.datetime.now()

        stats = self.driver.stats()
        self.assertIn('client', stats)
        self.assertIn('transport', stats)
        self.assertIn('connected', stats)
        self.assertIn('packets_sent', stats)
        self.assertIn('packets_received', stats)
        self.assertEqual(stats['packets_sent'], 5)
        self.assertEqual(stats['packets_received'], 10)

    def test_stats_serializable(self):
        """Test stats() with serializable=True."""
        self.driver._connected = True
        self.driver.last_packet_sent = datetime.datetime.now()
        self.driver.last_packet_received = datetime.datetime.now()

        stats = self.driver.stats(serializable=True)
        self.assertIsInstance(stats['last_packet_sent'], str)
        self.assertIsInstance(stats['last_packet_received'], str)
        self.assertIsInstance(stats['connection_keepalive'], str)

    def test_stats_none_times(self):
        """Test stats() with None times."""
        self.driver.last_packet_sent = None
        self.driver.last_packet_received = None

        stats = self.driver.stats(serializable=True)
        self.assertEqual(stats['last_packet_sent'], 'None')
        self.assertEqual(stats['last_packet_received'], 'None')
