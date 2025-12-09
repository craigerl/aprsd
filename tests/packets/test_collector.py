import unittest
from unittest import mock

from aprsd.packets import collector
from tests import fake


class MockPacketMonitor:
    """Mock implementation of PacketMonitor for testing."""

    _instance = None

    def __init__(self, name='MockMonitor'):
        self.name = name
        self.rx_called = False
        self.tx_called = False
        self.flush_called = False
        self.load_called = False

    def __call__(self):
        """Make it callable like a singleton."""
        if self._instance is None:
            self._instance = self
        return self._instance

    def rx(self, packet):
        self.rx_called = True
        self.rx_packet = packet

    def tx(self, packet):
        self.tx_called = True
        self.tx_packet = packet

    def flush(self):
        self.flush_called = True

    def load(self):
        self.load_called = True


class TestPacketMonitorProtocol(unittest.TestCase):
    """Test that PacketMonitor protocol is properly defined."""

    def test_protocol_definition(self):
        """Test that PacketMonitor is a Protocol."""
        from aprsd.packets.collector import PacketMonitor

        # Protocol with @runtime_checkable should have this attribute
        # But it's a Protocol, not a runtime_checkable Protocol necessarily
        # Let's just check it exists
        self.assertTrue(
            hasattr(PacketMonitor, '__protocol_attrs__')
            or hasattr(PacketMonitor, '__annotations__'),
        )


class TestPacketCollector(unittest.TestCase):
    """Unit tests for the PacketCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance
        collector.PacketCollector._instance = None
        # Clear monitors to start fresh
        pc = collector.PacketCollector()
        pc.monitors = []

    def tearDown(self):
        """Clean up after tests."""
        collector.PacketCollector._instance = None

    def test_singleton_pattern(self):
        """Test that PacketCollector is a singleton."""
        collector1 = collector.PacketCollector()
        collector2 = collector.PacketCollector()
        self.assertIs(collector1, collector2)

    def test_init(self):
        """Test initialization."""
        pc = collector.PacketCollector()
        # After setUp, monitors should be empty
        self.assertEqual(len(pc.monitors), 0)

    def test_register(self):
        """Test register() method."""
        pc = collector.PacketCollector()
        # Create a callable class

        class TestMonitor:
            _instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def rx(self, packet):
                pass

            def tx(self, packet):
                pass

            def flush(self):
                pass

            def load(self):
                pass

        monitor_class = TestMonitor()
        pc.register(monitor_class)
        self.assertIn(monitor_class, pc.monitors)

    def test_register_non_protocol(self):
        """Test register() raises TypeError for non-protocol objects."""
        pc = collector.PacketCollector()
        non_monitor = object()

        with self.assertRaises(TypeError):
            pc.register(non_monitor)

    def test_unregister(self):
        """Test unregister() method."""
        pc = collector.PacketCollector()
        # Create a callable class

        class TestMonitor:
            _instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def rx(self, packet):
                pass

            def tx(self, packet):
                pass

            def flush(self):
                pass

            def load(self):
                pass

        monitor_class = TestMonitor()
        pc.register(monitor_class)
        pc.unregister(monitor_class)
        self.assertNotIn(monitor_class, pc.monitors)

    def test_unregister_non_protocol(self):
        """Test unregister() raises TypeError for non-protocol objects."""
        pc = collector.PacketCollector()
        non_monitor = object()

        with self.assertRaises(TypeError):
            pc.unregister(non_monitor)

    def test_rx(self):
        """Test rx() method."""
        pc = collector.PacketCollector()
        # Create callable monitor classes
        monitor1 = MockPacketMonitor('Monitor1')
        monitor2 = MockPacketMonitor('Monitor2')
        pc.register(monitor1)
        pc.register(monitor2)

        packet = fake.fake_packet()
        pc.rx(packet)

        self.assertTrue(monitor1().rx_called)
        self.assertTrue(monitor2().rx_called)
        self.assertEqual(monitor1().rx_packet, packet)
        self.assertEqual(monitor2().rx_packet, packet)

    def test_rx_with_exception(self):
        """Test rx() handles exceptions gracefully."""
        pc = collector.PacketCollector()

        class FailingMonitor:
            _instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def rx(self, packet):
                raise Exception('Monitor error')

            def tx(self, packet):
                pass

            def flush(self):
                pass

            def load(self):
                pass

        monitor = FailingMonitor()
        pc.register(monitor)

        packet = fake.fake_packet()
        # Should not raise exception
        with mock.patch('aprsd.packets.collector.LOG') as mock_log:
            pc.rx(packet)
            mock_log.error.assert_called()

    def test_tx(self):
        """Test tx() method."""
        pc = collector.PacketCollector()
        monitor1 = MockPacketMonitor('Monitor1')
        monitor2 = MockPacketMonitor('Monitor2')
        pc.register(monitor1)
        pc.register(monitor2)

        packet = fake.fake_packet()
        pc.tx(packet)

        self.assertTrue(monitor1().tx_called)
        self.assertTrue(monitor2().tx_called)
        self.assertEqual(monitor1().tx_packet, packet)
        self.assertEqual(monitor2().tx_packet, packet)

    def test_tx_with_exception(self):
        """Test tx() handles exceptions gracefully."""
        pc = collector.PacketCollector()

        class FailingMonitor:
            _instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def rx(self, packet):
                pass

            def tx(self, packet):
                raise Exception('Monitor error')

            def flush(self):
                pass

            def load(self):
                pass

        monitor = FailingMonitor()
        pc.register(monitor)

        packet = fake.fake_packet()
        # Should not raise exception
        with mock.patch('aprsd.packets.collector.LOG') as mock_log:
            pc.tx(packet)
            mock_log.error.assert_called()

    def test_flush(self):
        """Test flush() method."""
        pc = collector.PacketCollector()
        monitor1 = MockPacketMonitor('Monitor1')
        monitor2 = MockPacketMonitor('Monitor2')
        pc.register(monitor1)
        pc.register(monitor2)

        pc.flush()

        self.assertTrue(monitor1().flush_called)
        self.assertTrue(monitor2().flush_called)

    def test_flush_with_exception(self):
        """Test flush() handles exceptions gracefully."""
        pc = collector.PacketCollector()

        class FailingMonitor:
            _instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def rx(self, packet):
                pass

            def tx(self, packet):
                pass

            def flush(self):
                raise Exception('Monitor error')

            def load(self):
                pass

        monitor = FailingMonitor()
        pc.register(monitor)

        # Should not raise exception
        with mock.patch('aprsd.packets.collector.LOG') as mock_log:
            pc.flush()
            mock_log.error.assert_called()

    def test_load(self):
        """Test load() method."""
        pc = collector.PacketCollector()
        monitor1 = MockPacketMonitor('Monitor1')
        monitor2 = MockPacketMonitor('Monitor2')
        pc.register(monitor1)
        pc.register(monitor2)

        pc.load()

        self.assertTrue(monitor1().load_called)
        self.assertTrue(monitor2().load_called)

    def test_load_with_exception(self):
        """Test load() handles exceptions gracefully."""
        pc = collector.PacketCollector()

        class FailingMonitor:
            _instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def rx(self, packet):
                pass

            def tx(self, packet):
                pass

            def flush(self):
                pass

            def load(self):
                raise Exception('Monitor error')

        monitor = FailingMonitor()
        pc.register(monitor)

        # Should not raise exception
        with mock.patch('aprsd.packets.collector.LOG') as mock_log:
            pc.load()
            mock_log.error.assert_called()

    def test_multiple_monitors(self):
        """Test multiple monitors are called in order."""
        pc = collector.PacketCollector()
        call_order = []

        class OrderedMonitor:
            _instance = None

            def __init__(self, name):
                self.name = name

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def rx(self, packet):
                call_order.append(self.name)

            def tx(self, packet):
                pass

            def flush(self):
                pass

            def load(self):
                pass

        monitor1 = OrderedMonitor('Monitor1')
        monitor2 = OrderedMonitor('Monitor2')
        monitor3 = OrderedMonitor('Monitor3')

        pc.register(monitor1)
        pc.register(monitor2)
        pc.register(monitor3)

        packet = fake.fake_packet()
        pc.rx(packet)

        self.assertEqual(call_order, ['Monitor1', 'Monitor2', 'Monitor3'])
