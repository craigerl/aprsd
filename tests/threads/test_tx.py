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
        # Reset scheduler instances
        tx._packet_scheduler = None
        tx._ack_scheduler = None

    def tearDown(self):
        """Clean up after tests."""
        tracker.PacketTrack._instance = None
        # Clean up schedulers
        if tx._packet_scheduler:
            tx._packet_scheduler.stop()
            if tx._packet_scheduler.is_alive():
                tx._packet_scheduler.join(timeout=1)
        if tx._ack_scheduler:
            tx._ack_scheduler.stop()
            if tx._ack_scheduler.is_alive():
                tx._ack_scheduler.join(timeout=1)
        tx._packet_scheduler = None
        tx._ack_scheduler = None

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

    @mock.patch('aprsd.threads.tx._get_packet_scheduler')
    def test_send_packet_threaded(self, mock_get_scheduler):
        """Test _send_packet() uses scheduler."""
        packet = fake.fake_packet()
        mock_scheduler = mock.MagicMock()
        mock_scheduler.is_alive.return_value = True
        mock_get_scheduler.return_value = mock_scheduler

        tx._send_packet(packet, direct=False)

        mock_get_scheduler.assert_called()
        # Scheduler should be alive and will handle the packet
        self.assertTrue(mock_scheduler.is_alive())

    @mock.patch('aprsd.threads.tx.SendPacketThread')
    @mock.patch('aprsd.threads.tx._get_packet_scheduler')
    def test_send_packet_fallback(self, mock_get_scheduler, mock_thread_class):
        """Test _send_packet() falls back to old method if scheduler not available."""
        packet = fake.fake_packet()
        mock_scheduler = mock.MagicMock()
        mock_scheduler.is_alive.return_value = False
        mock_get_scheduler.return_value = mock_scheduler
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

    @mock.patch('aprsd.threads.tx._get_ack_scheduler')
    def test_send_ack_threaded(self, mock_get_scheduler):
        """Test _send_ack() uses scheduler."""
        packet = fake.fake_ack_packet()
        mock_scheduler = mock.MagicMock()
        mock_scheduler.is_alive.return_value = True
        mock_get_scheduler.return_value = mock_scheduler

        tx._send_ack(packet, direct=False)

        mock_get_scheduler.assert_called()
        # Scheduler should be alive and will handle the packet
        self.assertTrue(mock_scheduler.is_alive())

    @mock.patch('aprsd.threads.tx.SendAckThread')
    @mock.patch('aprsd.threads.tx._get_ack_scheduler')
    def test_send_ack_fallback(self, mock_get_scheduler, mock_thread_class):
        """Test _send_ack() falls back to old method if scheduler not available."""
        packet = fake.fake_ack_packet()
        mock_scheduler = mock.MagicMock()
        mock_scheduler.is_alive.return_value = False
        mock_get_scheduler.return_value = mock_scheduler
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

    @mock.patch('aprsd.threads.tx.PacketSendSchedulerThread')
    def test_get_packet_scheduler_creates_new(self, mock_scheduler_class):
        """Test _get_packet_scheduler() creates new scheduler if none exists."""
        tx._packet_scheduler = None
        mock_scheduler = mock.MagicMock()
        mock_scheduler_class.return_value = mock_scheduler

        result = tx._get_packet_scheduler()

        mock_scheduler_class.assert_called_once()
        mock_scheduler.start.assert_called_once()
        self.assertEqual(result, mock_scheduler)

    @mock.patch('aprsd.threads.tx.PacketSendSchedulerThread')
    def test_get_packet_scheduler_reuses_existing(self, mock_scheduler_class):
        """Test _get_packet_scheduler() reuses existing scheduler if alive."""
        existing_scheduler = mock.MagicMock()
        existing_scheduler.is_alive.return_value = True
        tx._packet_scheduler = existing_scheduler

        result = tx._get_packet_scheduler()

        mock_scheduler_class.assert_not_called()
        self.assertEqual(result, existing_scheduler)

    @mock.patch('aprsd.threads.tx.PacketSendSchedulerThread')
    def test_get_packet_scheduler_recreates_if_dead(self, mock_scheduler_class):
        """Test _get_packet_scheduler() recreates scheduler if dead."""
        dead_scheduler = mock.MagicMock()
        dead_scheduler.is_alive.return_value = False
        tx._packet_scheduler = dead_scheduler
        new_scheduler = mock.MagicMock()
        mock_scheduler_class.return_value = new_scheduler

        result = tx._get_packet_scheduler()

        mock_scheduler_class.assert_called_once()
        new_scheduler.start.assert_called_once()
        self.assertEqual(result, new_scheduler)

    @mock.patch('aprsd.threads.tx.AckSendSchedulerThread')
    def test_get_ack_scheduler_creates_new(self, mock_scheduler_class):
        """Test _get_ack_scheduler() creates new scheduler if none exists."""
        tx._ack_scheduler = None
        mock_scheduler = mock.MagicMock()
        mock_scheduler_class.return_value = mock_scheduler

        result = tx._get_ack_scheduler()

        mock_scheduler_class.assert_called_once()
        mock_scheduler.start.assert_called_once()
        self.assertEqual(result, mock_scheduler)


class TestPacketWorkers(unittest.TestCase):
    """Unit tests for worker functions used by threadpool."""

    def setUp(self):
        """Set up test fixtures."""
        tracker.PacketTrack._instance = None

    def tearDown(self):
        """Clean up after tests."""
        tracker.PacketTrack._instance = None

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_send_packet_worker_packet_acked(self, mock_tracker_class):
        """Test _send_packet_worker() when packet is acked."""
        mock_tracker = mock.MagicMock()
        mock_tracker.get.return_value = None  # Packet removed = acked
        mock_tracker_class.return_value = mock_tracker

        result = tx._send_packet_worker('123')
        self.assertFalse(result)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_send_packet_worker_max_retries(self, mock_tracker_class):
        """Test _send_packet_worker() when max retries reached."""
        mock_tracker = mock.MagicMock()
        tracked_packet = fake.fake_packet(msg_number='123')
        tracked_packet.send_count = 3
        tracked_packet.retry_count = 3
        mock_tracker.get.return_value = tracked_packet
        mock_tracker_class.return_value = mock_tracker

        with mock.patch('aprsd.threads.tx.LOG') as mock_log:
            result = tx._send_packet_worker('123')
            self.assertFalse(result)
            mock_log.info.assert_called()
            mock_tracker.remove.assert_called()

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    @mock.patch('aprsd.threads.tx._send_direct')
    def test_send_packet_worker_send_now(self, mock_send_direct, mock_tracker_class):
        """Test _send_packet_worker() when it's time to send."""
        mock_tracker = mock.MagicMock()
        tracked_packet = fake.fake_packet(msg_number='123')
        tracked_packet.send_count = 0
        tracked_packet.retry_count = 3
        tracked_packet.last_send_time = None
        mock_tracker.get.return_value = tracked_packet
        mock_tracker_class.return_value = mock_tracker

        mock_send_direct.return_value = True

        result = tx._send_packet_worker('123')

        self.assertTrue(result)
        mock_send_direct.assert_called()
        self.assertEqual(tracked_packet.send_count, 1)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    @mock.patch('aprsd.threads.tx._send_direct')
    def test_send_packet_worker_send_failed(self, mock_send_direct, mock_tracker_class):
        """Test _send_packet_worker() when send fails."""
        mock_tracker = mock.MagicMock()
        tracked_packet = fake.fake_packet(msg_number='123')
        tracked_packet.send_count = 0
        tracked_packet.retry_count = 3
        tracked_packet.last_send_time = None
        mock_tracker.get.return_value = tracked_packet
        mock_tracker_class.return_value = mock_tracker

        mock_send_direct.return_value = False

        result = tx._send_packet_worker('123')

        self.assertTrue(result)
        self.assertEqual(
            tracked_packet.send_count, 0
        )  # Should not increment on failure

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_send_ack_worker_packet_removed(self, mock_tracker_class):
        """Test _send_ack_worker() when packet is removed."""
        mock_tracker = mock.MagicMock()
        mock_tracker.get.return_value = None
        mock_tracker_class.return_value = mock_tracker

        result = tx._send_ack_worker('123', 3)
        self.assertFalse(result)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_send_ack_worker_max_retries(self, mock_tracker_class):
        """Test _send_ack_worker() when max retries reached."""
        mock_tracker = mock.MagicMock()
        tracked_packet = fake.fake_ack_packet()
        tracked_packet.send_count = 3
        mock_tracker.get.return_value = tracked_packet
        mock_tracker_class.return_value = mock_tracker

        with mock.patch('aprsd.threads.tx.LOG') as mock_log:
            result = tx._send_ack_worker('123', 3)
            self.assertFalse(result)
            mock_log.debug.assert_called()

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    @mock.patch('aprsd.threads.tx._send_direct')
    def test_send_ack_worker_send_now(self, mock_send_direct, mock_tracker_class):
        """Test _send_ack_worker() when it's time to send."""
        mock_tracker = mock.MagicMock()
        tracked_packet = fake.fake_ack_packet()
        tracked_packet.send_count = 0
        tracked_packet.last_send_time = None
        mock_tracker.get.return_value = tracked_packet
        mock_tracker_class.return_value = mock_tracker

        mock_send_direct.return_value = True

        result = tx._send_ack_worker('123', 3)

        self.assertTrue(result)
        mock_send_direct.assert_called()
        self.assertEqual(tracked_packet.send_count, 1)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    @mock.patch('aprsd.threads.tx._send_direct')
    def test_send_ack_worker_waiting(self, mock_send_direct, mock_tracker_class):
        """Test _send_ack_worker() when waiting for next send."""
        mock_tracker = mock.MagicMock()
        tracked_packet = fake.fake_ack_packet()
        tracked_packet.send_count = 0
        tracked_packet.last_send_time = int(time.time()) - 10  # Too soon
        mock_tracker.get.return_value = tracked_packet
        mock_tracker_class.return_value = mock_tracker

        mock_send_direct.return_value = True

        result = tx._send_ack_worker('123', 3)

        self.assertTrue(result)
        mock_send_direct.assert_not_called()


class TestPacketSendSchedulerThread(unittest.TestCase):
    """Unit tests for PacketSendSchedulerThread class."""

    def setUp(self):
        """Set up test fixtures."""
        tracker.PacketTrack._instance = None
        self.scheduler = tx.PacketSendSchedulerThread(max_workers=2)

    def tearDown(self):
        """Clean up after tests."""
        self.scheduler.stop()
        if self.scheduler.is_alive():
            self.scheduler.join(timeout=1)
        self.scheduler.executor.shutdown(wait=False)
        tracker.PacketTrack._instance = None

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.scheduler.name, 'PacketSendSchedulerThread')
        self.assertEqual(self.scheduler.max_workers, 2)
        self.assertIsNotNone(self.scheduler.executor)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_loop_submits_tasks(self, mock_tracker_class):
        """Test loop() submits tasks to threadpool."""
        mock_tracker = mock.MagicMock()
        packet1 = fake.fake_packet(msg_number='123')
        packet1.send_count = 0
        packet1.retry_count = 3
        packet2 = fake.fake_packet(msg_number='456')
        packet2.send_count = 0
        packet2.retry_count = 3
        mock_tracker.keys.return_value = ['123', '456']
        mock_tracker.get.side_effect = lambda x: packet1 if x == '123' else packet2
        mock_tracker_class.return_value = mock_tracker

        # Mock the executor's submit method
        with mock.patch.object(self.scheduler.executor, 'submit') as mock_submit:
            result = self.scheduler.loop()

            self.assertTrue(result)
            # Should submit tasks for both packets
            self.assertEqual(mock_submit.call_count, 2)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_loop_skips_acked_packets(self, mock_tracker_class):
        """Test loop() skips packets that are acked."""
        mock_tracker = mock.MagicMock()
        mock_tracker.keys.return_value = ['123']
        mock_tracker.get.return_value = None  # Packet acked
        mock_tracker_class.return_value = mock_tracker

        # Mock the executor's submit method
        with mock.patch.object(self.scheduler.executor, 'submit') as mock_submit:
            result = self.scheduler.loop()

            self.assertTrue(result)
            # Should not submit task for acked packet
            mock_submit.assert_not_called()

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_loop_skips_ack_packets(self, mock_tracker_class):
        """Test loop() skips AckPackets."""
        mock_tracker = mock.MagicMock()
        ack_packet = fake.fake_ack_packet()
        mock_tracker.keys.return_value = ['123']
        mock_tracker.get.return_value = ack_packet
        mock_tracker_class.return_value = mock_tracker

        # Mock the executor's submit method
        with mock.patch.object(self.scheduler.executor, 'submit') as mock_submit:
            result = self.scheduler.loop()

            self.assertTrue(result)
            # Should not submit task for ack packet
            mock_submit.assert_not_called()

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_loop_skips_max_retries(self, mock_tracker_class):
        """Test loop() skips packets at max retries."""
        mock_tracker = mock.MagicMock()
        packet = fake.fake_packet(msg_number='123')
        packet.send_count = 3
        packet.retry_count = 3
        mock_tracker.keys.return_value = ['123']
        mock_tracker.get.return_value = packet
        mock_tracker_class.return_value = mock_tracker

        # Mock the executor's submit method
        with mock.patch.object(self.scheduler.executor, 'submit') as mock_submit:
            result = self.scheduler.loop()

            self.assertTrue(result)
            # Should not submit task for packet at max retries
            mock_submit.assert_not_called()

    def test_cleanup(self):
        """Test _cleanup() shuts down executor."""
        with mock.patch.object(self.scheduler.executor, 'shutdown') as mock_shutdown:
            with mock.patch('aprsd.threads.tx.LOG') as mock_log:
                self.scheduler._cleanup()
                mock_shutdown.assert_called_once_with(wait=True)
                mock_log.debug.assert_called()


class TestAckSendSchedulerThread(unittest.TestCase):
    """Unit tests for AckSendSchedulerThread class."""

    def setUp(self):
        """Set up test fixtures."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.default_ack_send_count = 3
        tracker.PacketTrack._instance = None
        self.scheduler = tx.AckSendSchedulerThread(max_workers=2)

    def tearDown(self):
        """Clean up after tests."""
        self.scheduler.stop()
        if self.scheduler.is_alive():
            self.scheduler.join(timeout=1)
        self.scheduler.executor.shutdown(wait=False)
        tracker.PacketTrack._instance = None

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.scheduler.name, 'AckSendSchedulerThread')
        self.assertEqual(self.scheduler.max_workers, 2)
        self.assertEqual(self.scheduler.max_retries, 3)
        self.assertIsNotNone(self.scheduler.executor)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_loop_submits_tasks(self, mock_tracker_class):
        """Test loop() submits tasks to threadpool."""
        mock_tracker = mock.MagicMock()
        ack_packet1 = fake.fake_ack_packet()
        ack_packet1.send_count = 0
        ack_packet2 = fake.fake_ack_packet()
        ack_packet2.send_count = 0
        mock_tracker.keys.return_value = ['123', '456']
        mock_tracker.get.side_effect = lambda x: (
            ack_packet1 if x == '123' else ack_packet2
        )
        mock_tracker_class.return_value = mock_tracker

        # Mock the executor's submit method
        with mock.patch.object(self.scheduler.executor, 'submit') as mock_submit:
            result = self.scheduler.loop()

            self.assertTrue(result)
            # Should submit tasks for both ack packets
            self.assertEqual(mock_submit.call_count, 2)

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_loop_skips_non_ack_packets(self, mock_tracker_class):
        """Test loop() skips non-AckPackets."""
        mock_tracker = mock.MagicMock()
        regular_packet = fake.fake_packet()
        mock_tracker.keys.return_value = ['123']
        mock_tracker.get.return_value = regular_packet
        mock_tracker_class.return_value = mock_tracker

        # Mock the executor's submit method
        with mock.patch.object(self.scheduler.executor, 'submit') as mock_submit:
            result = self.scheduler.loop()

            self.assertTrue(result)
            # Should not submit task for non-ack packet
            mock_submit.assert_not_called()

    @mock.patch('aprsd.threads.tx.tracker.PacketTrack')
    def test_loop_skips_max_retries(self, mock_tracker_class):
        """Test loop() skips acks at max retries."""
        mock_tracker = mock.MagicMock()
        ack_packet = fake.fake_ack_packet()
        ack_packet.send_count = 3
        mock_tracker.keys.return_value = ['123']
        mock_tracker.get.return_value = ack_packet
        mock_tracker_class.return_value = mock_tracker

        # Mock the executor's submit method
        with mock.patch.object(self.scheduler.executor, 'submit') as mock_submit:
            result = self.scheduler.loop()

            self.assertTrue(result)
            # Should not submit task for ack at max retries
            mock_submit.assert_not_called()

    def test_cleanup(self):
        """Test _cleanup() shuts down executor."""
        with mock.patch.object(self.scheduler.executor, 'shutdown') as mock_shutdown:
            with mock.patch('aprsd.threads.tx.LOG') as mock_log:
                self.scheduler._cleanup()
                mock_shutdown.assert_called_once_with(wait=True)
                mock_log.debug.assert_called()


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
