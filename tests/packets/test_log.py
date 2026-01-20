import unittest
from unittest import mock

from aprsd import packets
from aprsd.packets import log
from tests import fake


class TestPacketLog(unittest.TestCase):
    """Unit tests for the packet logging functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the logging to avoid actual log output during tests
        self.loguru_opt_mock = mock.patch('aprsd.packets.log.LOGU.opt').start()
        self.loguru_info_mock = self.loguru_opt_mock.return_value.info
        self.logging_mock = mock.patch('aprsd.packets.log.LOG').start()
        self.haversine_mock = mock.patch('aprsd.packets.log.haversine').start()
        self.utils_mock = mock.patch('aprsd.packets.log.utils').start()
        self.conf_mock = mock.patch('aprsd.packets.log.CONF').start()

        # Set default configuration values
        self.conf_mock.enable_packet_logging = True
        self.conf_mock.log_packet_format = (
            'multiline'  # Changed from 'compact' to 'multiline'
        )
        self.conf_mock.default_ack_send_count = 3
        self.conf_mock.default_packet_send_count = 5
        self.conf_mock.latitude = 37.7749
        self.conf_mock.longitude = -122.4194

        # Set up the utils mock methods
        self.utils_mock.calculate_initial_compass_bearing.return_value = 45.0
        self.utils_mock.degrees_to_cardinal.return_value = 'NE'
        self.haversine_mock.return_value = 10.5

        # No need to mock packet.raw since we create real packets with raw data
        # The packet objects created in tests will have their raw attribute set properly

    def tearDown(self):
        """Clean up after tests."""
        # Stop all mocks
        mock.patch.stopall()

    def test_log_multiline_with_ack_packet(self):
        """Test log_multiline with an AckPacket."""
        # Create a fake AckPacket
        packet = fake.fake_ack_packet()
        packet.send_count = 1

        # Call the function
        log.log_multiline(packet, tx=True, header=True)

        # Verify that logging was called
        self.loguru_opt_mock.assert_called_once()
        self.loguru_info_mock.assert_called_once()
        # LOG.debug is no longer called in log_multiline

    def test_log_multiline_with_gps_packet(self):
        """Test log_multiline with a GPSPacket."""
        # Create a fake GPSPacket
        packet = packets.GPSPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            symbol='>',
            comment='Test GPS comment',
        )
        packet.send_count = 2

        # Call the function
        log.log_multiline(packet, tx=False, header=True)

        # Verify that logging was called
        self.loguru_opt_mock.assert_called_once()
        self.loguru_info_mock.assert_called_once()
        # LOG.debug is no longer called in log_multiline

    def test_log_multiline_disabled_logging(self):
        """Test log_multiline when packet logging is disabled."""
        # Disable packet logging
        self.conf_mock.enable_packet_logging = False

        # Create a fake packet
        packet = fake.fake_packet()
        packet.send_count = 0

        # Call the function
        log.log_multiline(packet, tx=False, header=True)

        # Verify that logging was NOT called
        self.loguru_opt_mock.assert_not_called()
        self.logging_mock.debug.assert_not_called()

    def test_log_multiline_compact_format(self):
        """Test log_multiline when log format is compact."""
        # Set compact format
        self.conf_mock.log_packet_format = 'compact'

        # Create a fake packet
        packet = fake.fake_packet()
        packet.send_count = 0

        # Call the function
        log.log_multiline(packet, tx=False, header=True)

        # Verify that logging was NOT called (because of compact format)
        self.loguru_opt_mock.assert_not_called()
        self.logging_mock.debug.assert_not_called()

    def test_log_with_compact_format(self):
        """Test log function with compact format."""
        # Set compact format
        self.conf_mock.log_packet_format = 'compact'

        # Create a fake packet
        packet = fake.fake_packet()
        packet.send_count = 1

        # Call the function
        log.log(packet, tx=True, header=True, packet_count=1)

        # Verify that logging was called (but may be different behavior)
        self.loguru_opt_mock.assert_called_once()

    def test_log_with_multiline_format(self):
        """Test log function with multiline format."""
        # Set multiline format
        self.conf_mock.log_packet_format = 'multiline'

        # Create a fake packet
        packet = fake.fake_packet()
        packet.send_count = 1

        # Call the function
        log.log(packet, tx=True, header=True, packet_count=1)

        # Verify that logging was called
        self.loguru_opt_mock.assert_called_once()

    def test_log_with_gps_packet_distance(self):
        """Test log function with GPS packet that includes distance info."""
        # Create a GPSPacket
        packet = packets.GPSPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            symbol='>',
            comment='Test GPS comment',
        )
        packet.send_count = 2

        # Call the function
        log.log(packet, tx=False, header=True)

        # Verify that logging was called
        self.loguru_opt_mock.assert_called_once()

    def test_log_with_disabled_logging(self):
        """Test log function when packet logging is disabled."""
        # Disable packet logging
        self.conf_mock.enable_packet_logging = False

        # Create a fake packet
        packet = fake.fake_packet()
        packet.send_count = 0

        # Call the function
        log.log(packet, tx=False, header=True, force_log=False)

        # Verify that logging was NOT called
        self.loguru_opt_mock.assert_not_called()

    def test_log_with_force_log(self):
        """Test log function with force_log=True even when logging is disabled."""
        # Disable packet logging
        self.conf_mock.enable_packet_logging = False

        # Create a fake packet
        packet = fake.fake_packet()
        packet.send_count = 0

        # Call the function with force_log=True
        log.log(packet, tx=False, header=True, force_log=True)

        # Verify that logging WAS called because of force_log=True
        self.loguru_opt_mock.assert_called_once()

    def test_log_with_different_packet_types(self):
        """Test log function with different packet types."""
        # Test with MessagePacket
        packet = fake.fake_packet()
        packet.send_count = 1

        log.log(packet, tx=False, header=True)
        self.loguru_opt_mock.assert_called_once()

        # Reset mocks
        self.loguru_opt_mock.reset_mock()

        # Test with AckPacket
        ack_packet = fake.fake_ack_packet()
        ack_packet.send_count = 2

        log.log(ack_packet, tx=True, header=True)
        self.loguru_opt_mock.assert_called_once()
