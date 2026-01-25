import queue
import unittest
from unittest import mock

from aprsd.threads import rx
from tests import fake
from tests.mock_client_driver import MockClientDriver


class TestAPRSDRXThread(unittest.TestCase):
    """Unit tests for the APRSDRXThread class."""

    def setUp(self):
        """Set up test fixtures."""
        self.packet_queue = queue.Queue()
        self.rx_thread = rx.APRSDRXThread(self.packet_queue)
        self.rx_thread.pkt_count = 0  # Reset packet count
        # Mock time.sleep to speed up tests
        self.sleep_patcher = mock.patch('aprsd.threads.rx.time.sleep')
        self.mock_sleep = self.sleep_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.rx_thread.stop()
        if self.rx_thread.is_alive():
            self.rx_thread.join(timeout=1)
        # Stop the sleep patcher
        self.sleep_patcher.stop()

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.rx_thread.name, 'RX_PKT')
        self.assertEqual(self.rx_thread.packet_queue, self.packet_queue)
        self.assertEqual(self.rx_thread.pkt_count, 0)
        self.assertIsNone(self.rx_thread._client)

    def test_stop(self):
        """Test stop() method."""
        self.rx_thread._client = mock.MagicMock()
        self.rx_thread.stop()

        self.assertTrue(self.rx_thread.thread_stop)
        self.rx_thread._client.close.assert_called()

    def test_stop_no_client(self):
        """Test stop() when client is None."""
        self.rx_thread.stop()
        self.assertTrue(self.rx_thread.thread_stop)

    def test_loop_no_client(self):
        """Test loop() when client is None."""
        with mock.patch('aprsd.threads.rx.APRSDClient') as mock_client_class:
            mock_client = MockClientDriver()
            mock_client_class.return_value = mock_client

            result = self.rx_thread.loop()

            self.assertTrue(result)
            self.assertIsNotNone(self.rx_thread._client)

    def test_loop_client_not_alive(self):
        """Test loop() when client is not alive."""
        from aprsd.client.client import APRSDClient

        # Reset singleton
        APRSDClient._instance = None

        mock_client = MockClientDriver()
        mock_client._alive = False
        self.rx_thread._client = mock_client

        with mock.patch('aprsd.threads.rx.APRSDClient') as mock_client_class:
            new_client_instance = mock.MagicMock()
            new_client_instance.driver = MockClientDriver()
            new_client_instance.is_alive = True
            mock_client_class.return_value = new_client_instance

            result = self.rx_thread.loop()

            self.assertTrue(result)
            # Client should be replaced
            self.assertIsNotNone(self.rx_thread._client)

    def test_loop_consumer_success(self):
        """Test loop() with successful consumer call."""
        mock_client = MockClientDriver()
        mock_client._alive = True
        callback_called = []
        mock_client._consumer_callback = lambda cb: callback_called.append(True)
        self.rx_thread._client = mock_client

        result = self.rx_thread.loop()

        self.assertTrue(result)
        self.assertTrue(len(callback_called) > 0)

    def test_loop_connection_drop(self):
        """Test loop() handles ConnectionDrop exception."""
        import aprslib

        mock_client = MockClientDriver()
        mock_client._alive = True
        mock_client._consumer_side_effect = aprslib.exceptions.ConnectionDrop(
            'Connection dropped'
        )
        self.rx_thread._client = mock_client

        with mock.patch('aprsd.threads.rx.LOG') as mock_log:
            with mock.patch.object(mock_client, 'reset') as mock_reset:
                result = self.rx_thread.loop()
                self.assertTrue(result)
                mock_log.error.assert_called()
                mock_reset.assert_called()

    def test_loop_connection_error(self):
        """Test loop() handles ConnectionError exception."""
        import aprslib

        mock_client = MockClientDriver()
        mock_client._alive = True
        mock_client._consumer_side_effect = aprslib.exceptions.ConnectionError(
            'Connection error'
        )
        self.rx_thread._client = mock_client

        with mock.patch('aprsd.threads.rx.LOG') as mock_log:
            with mock.patch.object(mock_client, 'reset') as mock_reset:
                result = self.rx_thread.loop()
                self.assertTrue(result)
                mock_log.error.assert_called()
                mock_reset.assert_called()

    def test_loop_general_exception(self):
        """Test loop() handles general exceptions."""
        mock_client = MockClientDriver()
        mock_client._alive = True
        mock_client._consumer_side_effect = Exception('General error')
        self.rx_thread._client = mock_client

        with mock.patch('aprsd.threads.rx.LOG') as mock_log:
            with mock.patch.object(mock_client, 'reset') as mock_reset:
                result = self.rx_thread.loop()
                self.assertTrue(result)
                mock_log.exception.assert_called()
                mock_log.error.assert_called()
                mock_reset.assert_called()

    def test_process_packet(self):
        """Test process_packet() method."""
        mock_client = MockClientDriver()
        packet = fake.fake_packet(msg_number='123')
        mock_client._decode_packet_return = packet
        self.rx_thread._client = mock_client
        self.rx_thread.pkt_count = 0

        with mock.patch('aprsd.threads.rx.packet_log'):
            with mock.patch('aprsd.threads.rx.packets.PacketList') as mock_pkt_list:
                mock_list_instance = mock.MagicMock()
                mock_list_instance.find.side_effect = KeyError('Not found')
                mock_pkt_list.return_value = mock_list_instance

                # Pass raw packet string as args[0]
                self.rx_thread.process_packet(packet.raw)

                self.assertEqual(self.rx_thread.pkt_count, 1)
                self.assertFalse(self.packet_queue.empty())
                # Verify the raw string is on the queue
                queued_raw = self.packet_queue.get()
                self.assertEqual(queued_raw, packet.raw)

    def test_process_packet_no_packet(self):
        """Test process_packet() when no frame is received."""
        mock_client = MockClientDriver()
        mock_client._decode_packet_return = None
        self.rx_thread._client = mock_client
        self.rx_thread.pkt_count = 0

        with mock.patch('aprsd.threads.rx.LOG') as mock_log:
            # Call without args to trigger warning
            self.rx_thread.process_packet()
            mock_log.warning.assert_called()
            self.assertEqual(self.rx_thread.pkt_count, 0)

    def test_process_packet_ack_packet(self):
        """Test process_packet() with AckPacket."""
        mock_client = MockClientDriver()
        packet = fake.fake_ack_packet()
        mock_client._decode_packet_return = packet
        self.rx_thread._client = mock_client
        self.rx_thread.pkt_count = 0

        with mock.patch('aprsd.threads.rx.packet_log'):
            # Pass raw packet string as args[0]
            self.rx_thread.process_packet(packet.raw)

            self.assertEqual(self.rx_thread.pkt_count, 1)
            self.assertFalse(self.packet_queue.empty())
            # Verify the raw string is on the queue
            queued_raw = self.packet_queue.get()
            self.assertEqual(queued_raw, packet.raw)

    def test_process_packet_duplicate(self):
        """Test process_packet() with duplicate packet.

        Note: The rx thread's process_packet() doesn't filter duplicates.
        It puts all packets on the queue. Duplicate filtering happens
        later in the filter thread.
        """
        mock_client = MockClientDriver()
        packet = fake.fake_packet(msg_number='123')
        packet.processed = True
        packet.timestamp = 1000
        mock_client._decode_packet_return = packet
        self.rx_thread._client = mock_client
        self.rx_thread.pkt_count = 0

        with mock.patch('aprsd.threads.rx.packet_log'):
            # Pass raw packet string as args[0]
            self.rx_thread.process_packet(packet.raw)
            # The rx thread puts all packets on the queue regardless of duplicates
            # Duplicate filtering happens in the filter thread
            self.assertFalse(self.packet_queue.empty())
            queued_raw = self.packet_queue.get()
            # Verify the raw string is on the queue
            self.assertEqual(queued_raw, packet.raw)


class TestAPRSDFilterThread(unittest.TestCase):
    """Unit tests for the APRSDFilterThread class."""

    def setUp(self):
        """Set up test fixtures."""
        self.packet_queue = queue.Queue()

        class TestFilterThread(rx.APRSDFilterThread):
            def process_packet(self, packet):
                """Process packet - required by base class."""
                pass

        self.filter_thread = TestFilterThread('TestFilterThread', self.packet_queue)
        # Mock time.sleep to speed up tests
        self.sleep_patcher = mock.patch('aprsd.threads.rx.time.sleep')
        self.mock_sleep = self.sleep_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.filter_thread.stop()
        if self.filter_thread.is_alive():
            self.filter_thread.join(timeout=1)
        # Stop the sleep patcher
        self.sleep_patcher.stop()

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.filter_thread.name, 'TestFilterThread')
        self.assertEqual(self.filter_thread.packet_queue, self.packet_queue)

    def test_filter_packet(self):
        """Test filter_packet() method."""
        packet = fake.fake_packet()

        with mock.patch('aprsd.threads.rx.filter.PacketFilter') as mock_filter:
            mock_filter_instance = mock.MagicMock()
            mock_filter_instance.filter.return_value = packet
            mock_filter.return_value = mock_filter_instance

            result = self.filter_thread.filter_packet(packet)
            self.assertEqual(result, packet)

    def test_filter_packet_dropped(self):
        """Test filter_packet() when packet is dropped."""
        packet = fake.fake_packet()

        with mock.patch('aprsd.threads.rx.filter.PacketFilter') as mock_filter:
            mock_filter_instance = mock.MagicMock()
            mock_filter_instance.filter.return_value = None
            mock_filter.return_value = mock_filter_instance

            result = self.filter_thread.filter_packet(packet)
            self.assertIsNone(result)

    def test_print_packet(self):
        """Test print_packet() method."""
        packet = fake.fake_packet()
        self.filter_thread.packet_count = 5  # Set a packet count

        with mock.patch('aprsd.threads.rx.packet_log') as mock_log:
            self.filter_thread.print_packet(packet)
            mock_log.log.assert_called_with(packet, packet_count=5)

    def test_loop_with_packet(self):
        """Test loop() with packet in queue."""
        packet = fake.fake_packet()
        self.packet_queue.put(packet)

        with mock.patch.object(
            self.filter_thread, 'filter_packet', return_value=packet
        ):
            with mock.patch.object(self.filter_thread, 'print_packet'):
                result = self.filter_thread.loop()
                self.assertTrue(result)

    def test_loop_empty_queue(self):
        """Test loop() with empty queue."""
        result = self.filter_thread.loop()
        self.assertTrue(result)

    def test_loop_filtered_packet(self):
        """Test loop() when packet is filtered out."""
        packet = fake.fake_packet()
        self.packet_queue.put(packet)

        with mock.patch.object(self.filter_thread, 'filter_packet', return_value=None):
            with mock.patch.object(self.filter_thread, 'print_packet'):
                result = self.filter_thread.loop()
                self.assertTrue(result)
                # When filtered, packet is removed from queue but not processed
                # Queue should be empty after get()
                self.assertTrue(self.packet_queue.empty())


class TestAPRSDProcessPacketThread(unittest.TestCase):
    """Unit tests for the APRSDProcessPacketThread class."""

    def setUp(self):
        """Set up test fixtures."""
        self.packet_queue = queue.Queue()

        class ConcreteProcessThread(rx.APRSDProcessPacketThread):
            def process_our_message_packet(self, packet):
                pass

        self.process_thread = ConcreteProcessThread(self.packet_queue)
        # Mock time.sleep to speed up tests
        self.sleep_patcher = mock.patch('aprsd.threads.rx.time.sleep')
        self.mock_sleep = self.sleep_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.process_thread.stop()
        if self.process_thread.is_alive():
            self.process_thread.join(timeout=1)
        # Stop the sleep patcher
        self.sleep_patcher.stop()

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.process_thread.name, 'ProcessPKT')

    def test_process_ack_packet(self):
        """Test process_ack_packet() method."""
        from oslo_config import cfg

        from aprsd.packets import collector

        CONF = cfg.CONF
        CONF.callsign = 'TEST'

        packet = fake.fake_ack_packet()
        packet.addresse = 'TEST'

        with mock.patch.object(collector.PacketCollector(), 'rx') as mock_rx:
            self.process_thread.process_ack_packet(packet)
            mock_rx.assert_called_with(packet)

    def test_process_piggyback_ack(self):
        """Test process_piggyback_ack() method."""
        from aprsd.packets import collector

        packet = fake.fake_packet()
        packet.ackMsgNo = '123'

        with mock.patch.object(collector.PacketCollector(), 'rx') as mock_rx:
            self.process_thread.process_piggyback_ack(packet)
            mock_rx.assert_called_with(packet)

    def test_process_reject_packet(self):
        """Test process_reject_packet() method."""
        from aprsd.packets import collector

        packet = fake.fake_packet()
        packet.msgNo = '123'

        with mock.patch.object(collector.PacketCollector(), 'rx') as mock_rx:
            self.process_thread.process_reject_packet(packet)
            mock_rx.assert_called_with(packet)

    def test_process_other_packet(self):
        """Test process_other_packet() method."""
        packet = fake.fake_packet()

        with mock.patch('aprsd.threads.rx.LOG') as mock_log:
            self.process_thread.process_other_packet(packet, for_us=False)
            mock_log.info.assert_called()

            self.process_thread.process_other_packet(packet, for_us=True)
            self.assertEqual(mock_log.info.call_count, 2)
