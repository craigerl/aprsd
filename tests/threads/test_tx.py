import time
import unittest
from unittest import mock

from aprsd.packets import tracker
from aprsd.threads import tx
from tests import fake
from tests.mock_client_driver import MockClientDriver


class TestSendFunctions(unittest.TestCase):
    """Unit tests for send functions in tx module."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instances
        tracker.PacketTrack._instance = None

    def tearDown(self):
        """Clean up after tests."""
        tracker.PacketTrack._instance = None

    @mock.patch('aprsd.threads.tx.collector.PacketCollector')
    @mock.patch('aprsd.threads.tx._send_packet')
    def test_send_message_packet(self, mock_send_packet, mock_collector):
        """Test send() with MessagePacket."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.enable_sending_ack_packets = True

        packet = fake.fake_packet()
        tx.send(packet)

        mock_collector.return_value.tx.assert_called()
        mock_send_packet.assert_called()

    @mock.patch('aprsd.threads.tx.collector.PacketCollector')
    @mock.patch('aprsd.threads.tx._send_ack')
    def test_send_ack_packet(self, mock_send_ack, mock_collector):
        """Test send() with AckPacket."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.enable_sending_ack_packets = True

        packet = fake.fake_ack_packet()
        tx.send(packet)

        mock_collector.return_value.tx.assert_called()
        mock_send_ack.assert_called()

    @mock.patch('aprsd.threads.tx.collector.PacketCollector')
    @mock.patch('aprsd.threads.tx._send_ack')
    def test_send_ack_disabled(self, mock_send_ack, mock_collector):
        """Test send() with AckPacket when acks are disabled."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.enable_sending_ack_packets = False

        packet = fake.fake_ack_packet()

        with mock.patch('aprsd.threads.tx.LOG') as mock_log:
            tx.send(packet)
            mock_log.info.assert_called()
            mock_send_ack.assert_not_called()

    @mock.patch('aprsd.threads.tx.SendPacketThread')
    def test_send_packet_threaded(self, mock_thread_class):
        """Test _send_packet() with threading."""
        packet = fake.fake_packet()
        mock_thread = mock.MagicMock()
        mock_thread_class.return_value = mock_thread

        tx._send_packet(packet, direct=False)

        mock_thread_class.assert_called_with(packet=packet)
        mock_thread.start.assert_called()

    @mock.patch('aprsd.threads.tx._send_direct')
    def test_send_packet_direct(self, mock_send_direct):
        """Test _send_packet() with direct send."""
        packet = fake.fake_packet()
        tx._send_packet(packet, direct=True)
        mock_send_direct.assert_called_with(packet, aprs_client=None)

    @mock.patch('aprsd.threads.tx.SendAckThread')
    def test_send_ack_threaded(self, mock_thread_class):
        """Test _send_ack() with threading."""
        packet = fake.fake_ack_packet()
        mock_thread = mock.MagicMock()
        mock_thread_class.return_value = mock_thread

        tx._send_ack(packet, direct=False)

        mock_thread_class.assert_called_with(packet=packet)
        mock_thread.start.assert_called()

    @mock.patch('aprsd.threads.tx._send_direct')
    def test_send_ack_direct(self, mock_send_direct):
        """Test _send_ack() with direct send."""
        packet = fake.fake_ack_packet()
        tx._send_ack(packet, direct=True)
        mock_send_direct.assert_called_with(packet, aprs_client=None)

    @mock.patch('aprsd.threads.tx.APRSDClient')
    @mock.patch('aprsd.threads.tx.packet_log')
    def test_send_direct(self, mock_log, mock_client_class):
        """Test _send_direct() function."""
        packet = fake.fake_packet()
        mock_client = MockClientDriver()
        mock_client._send_return = True
        mock_client_class.return_value = mock_client

        result = tx._send_direct(packet)

        self.assertTrue(result)
        mock_log.log.assert_called()

    @mock.patch('aprsd.threads.tx.APRSDClient')
    @mock.patch('aprsd.threads.tx.packet_log')
    def test_send_direct_with_client(self, mock_log, mock_client_class):
        """Test _send_direct() with provided client."""
        packet = fake.fake_packet()
        mock_client = MockClientDriver()
        mock_client._send_return = True

        result = tx._send_direct(packet, aprs_client=mock_client)

        self.assertTrue(result)
        mock_client_class.assert_not_called()

    @mock.patch('aprsd.threads.tx.APRSDClient')
    @mock.patch('aprsd.threads.tx.packet_log')
    def test_send_direct_exception(self, mock_log, mock_client_class):
        """Test _send_direct() with exception."""
        packet = fake.fake_packet()
        mock_client = MockClientDriver()
        mock_client._send_side_effect = Exception('Send error')
        mock_client_class.return_value = mock_client

        with mock.patch('aprsd.threads.tx.LOG') as mock_log_error:
            result = tx._send_direct(packet)

            self.assertFalse(result)
            mock_log_error.error.assert_called()


class TestSendPacketThread(unittest.TestCase):
    """Unit tests for the SendPacketThread class."""

    def setUp(self):
        """Set up test fixtures."""
        tracker.PacketTrack._instance = None
        self.packet = fake.fake_packet(msg_number='123')
        self.thread = tx.SendPacketThread(self.packet)

    def tearDown(self):
        """Clean up after tests."""
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(timeout=1)
        tracker.PacketTrack._instance = None

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.thread.packet, self.packet)
        self.assertIn('TX-', self.thread.name)
        self.assertEqual(self.thread.loop_count, 1)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_loop_packet_acked(self, mock_tracker_class):
        """Test loop() when packet is acked."""
        mock_tracker = mock.MagicMock()
        mock_tracker.get.return_value = None  # Packet removed = acked
        mock_tracker_class.return_value = mock_tracker

        with mock.patch('aprsd.threads.tx.LOG') as mock_log:
            result = self.thread.loop()
            self.assertFalse(result)
            mock_log.info.assert_called()

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_loop_max_retries(self, mock_tracker_class):
        """Test loop() when max retries reached."""
        mock_tracker = mock.MagicMock()
        tracked_packet = fake.fake_packet(msg_number='123')
        tracked_packet.send_count = 3
        tracked_packet.retry_count = 3
        mock_tracker.get.return_value = tracked_packet
        mock_tracker_class.return_value = mock_tracker

        with mock.patch('aprsd.threads.tx.LOG') as mock_log:
            result = self.thread.loop()
            self.assertFalse(result)
            mock_log.info.assert_called()
            mock_tracker.remove.assert_called()

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    @mock.patch('aprsd.threads.tx._send_direct')
    def test_loop_send_now(self, mock_send_direct, mock_tracker_class):
        """Test loop() when it's time to send."""
        mock_tracker = mock.MagicMock()
        tracked_packet = fake.fake_packet(msg_number='123')
        tracked_packet.send_count = 0
        tracked_packet.retry_count = 3
        tracked_packet.last_send_time = None
        mock_tracker.get.return_value = tracked_packet
        mock_tracker_class.return_value = mock_tracker

        mock_send_direct.return_value = True

        result = self.thread.loop()

        self.assertTrue(result)
        mock_send_direct.assert_called()
        self.assertEqual(tracked_packet.send_count, 1)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    @mock.patch('aprsd.threads.tx._send_direct')
    def test_loop_send_failed(self, mock_send_direct, mock_tracker_class):
        """Test loop() when send fails."""
        mock_tracker = mock.MagicMock()
        tracked_packet = fake.fake_packet(msg_number='123')
        tracked_packet.send_count = 0
        tracked_packet.retry_count = 3
        tracked_packet.last_send_time = None
        mock_tracker.get.return_value = tracked_packet
        mock_tracker_class.return_value = mock_tracker

        mock_send_direct.return_value = False

        result = self.thread.loop()

        self.assertTrue(result)
        self.assertEqual(
            tracked_packet.send_count, 0
        )  # Should not increment on failure


class TestSendAckThread(unittest.TestCase):
    """Unit tests for the SendAckThread class."""

    def setUp(self):
        """Set up test fixtures."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.default_ack_send_count = 3

        self.packet = fake.fake_ack_packet()
        self.packet.send_count = 0
        self.thread = tx.SendAckThread(self.packet)

    def tearDown(self):
        """Clean up after tests."""
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(timeout=1)

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.thread.packet, self.packet)
        self.assertIn('TXAck-', self.thread.name)
        self.assertEqual(self.thread.max_retries, 3)

    def test_loop_max_retries(self):
        """Test loop() when max retries reached."""
        self.packet.send_count = 3

        with mock.patch('aprsd.threads.tx.LOG') as mock_log:
            result = self.thread.loop()
            self.assertFalse(result)
            mock_log.debug.assert_called()

    @mock.patch('aprsd.threads.tx._send_direct')
    def test_loop_send_now(self, mock_send_direct):
        """Test loop() when it's time to send."""
        self.packet.last_send_time = None
        mock_send_direct.return_value = True

        result = self.thread.loop()

        self.assertTrue(result)
        mock_send_direct.assert_called()
        self.assertEqual(self.packet.send_count, 1)

    @mock.patch('aprsd.threads.tx._send_direct')
    def test_loop_waiting(self, mock_send_direct):
        """Test loop() when waiting for next send."""
        self.packet.last_send_time = int(time.time()) - 10  # Too soon
        mock_send_direct.return_value = True

        result = self.thread.loop()

        self.assertTrue(result)
        mock_send_direct.assert_not_called()


class TestBeaconSendThread(unittest.TestCase):
    """Unit tests for the BeaconSendThread class."""

    def setUp(self):
        """Set up test fixtures."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.latitude = 40.7128
        CONF.longitude = -74.0060
        CONF.beacon_interval = 10
        CONF.beacon_symbol = '>'
        CONF.callsign = 'TEST'

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_init(self):
        """Test initialization."""
        thread = tx.BeaconSendThread()
        self.assertEqual(thread.name, 'BeaconSendThread')
        self.assertEqual(thread._loop_cnt, 1)

    def test_init_no_coordinates(self):
        """Test initialization without coordinates."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.latitude = None
        CONF.longitude = None

        thread = tx.BeaconSendThread()
        self.assertTrue(thread.thread_stop)

    @mock.patch('aprsd.threads.tx.send')
    def test_loop_send_beacon(self, mock_send):
        """Test loop() sends beacon at interval."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.beacon_interval = 1

        thread = tx.BeaconSendThread()
        thread._loop_cnt = 1

        result = thread.loop()

        self.assertTrue(result)
        mock_send.assert_called()

    @mock.patch('aprsd.threads.tx.send')
    def test_loop_not_time(self, mock_send):
        """Test loop() doesn't send before interval."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.beacon_interval = 10

        thread = tx.BeaconSendThread()
        thread._loop_cnt = 5

        result = thread.loop()

        self.assertTrue(result)
        mock_send.assert_not_called()

    @mock.patch('aprsd.threads.tx.send')
    @mock.patch('aprsd.threads.tx.APRSDClient')
    def test_loop_send_exception(self, mock_client_class, mock_send):
        """Test loop() handles send exception."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.beacon_interval = 1

        thread = tx.BeaconSendThread()
        thread._loop_cnt = 1
        mock_send.side_effect = Exception('Send error')

        with mock.patch('aprsd.threads.tx.LOG') as mock_log:
            result = thread.loop()
            self.assertTrue(result)
            mock_log.error.assert_called()
            mock_client_class.return_value.reset.assert_called()
