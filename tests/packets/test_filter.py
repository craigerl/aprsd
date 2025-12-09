import unittest
from unittest import mock

from aprsd.packets import filter
from tests import fake


class MockPacketFilter:
    """Mock implementation of PacketFilterProtocol for testing."""

    def __init__(self, name='MockFilter', should_pass=True):
        self.name = name
        self.should_pass = should_pass
        self.filter_called = False

    def filter(self, packet):
        self.filter_called = True
        self.filtered_packet = packet
        return packet if self.should_pass else None


class TestPacketFilter(unittest.TestCase):
    """Unit tests for the PacketFilter class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance
        filter.PacketFilter._instance = None
        # Clear filters to start fresh
        pf = filter.PacketFilter()
        pf.filters = {}

    def tearDown(self):
        """Clean up after tests."""
        filter.PacketFilter._instance = None

    def test_singleton_pattern(self):
        """Test that PacketFilter is a singleton."""
        pf1 = filter.PacketFilter()
        pf2 = filter.PacketFilter()
        self.assertIs(pf1, pf2)

    def test_init(self):
        """Test initialization."""
        pf = filter.PacketFilter()
        # After setUp, filters should be empty
        self.assertEqual(pf.filters, {})

    def test_register(self):
        """Test register() method."""
        pf = filter.PacketFilter()

        class FilterClass:
            def filter(self, packet):
                return packet

        pf.register(FilterClass)
        self.assertIn(FilterClass, pf.filters)
        self.assertIsInstance(pf.filters[FilterClass], FilterClass)

    def test_register_non_protocol(self):
        """Test register() raises TypeError for non-protocol objects."""
        pf = filter.PacketFilter()
        non_filter = object()

        with self.assertRaises(TypeError):
            pf.register(non_filter)

    def test_register_duplicate(self):
        """Test register() doesn't create duplicate instances."""
        pf = filter.PacketFilter()

        class FilterClass:
            def filter(self, packet):
                return packet

        pf.register(FilterClass)
        instance1 = pf.filters[FilterClass]

        pf.register(FilterClass)
        instance2 = pf.filters[FilterClass]

        self.assertIs(instance1, instance2)

    def test_unregister(self):
        """Test unregister() method."""
        pf = filter.PacketFilter()

        class FilterClass:
            def filter(self, packet):
                return packet

        pf.register(FilterClass)
        pf.unregister(FilterClass)
        self.assertNotIn(FilterClass, pf.filters)

    def test_unregister_non_protocol(self):
        """Test unregister() raises TypeError for non-protocol objects."""
        pf = filter.PacketFilter()
        non_filter = object()

        with self.assertRaises(TypeError):
            pf.unregister(non_filter)

    def test_filter_passes(self):
        """Test filter() when all filters pass."""
        pf = filter.PacketFilter()

        class Filter1:
            def filter(self, packet):
                return packet

        class Filter2:
            def filter(self, packet):
                return packet

        pf.register(Filter1)
        pf.register(Filter2)

        packet = fake.fake_packet()
        result = pf.filter(packet)

        self.assertEqual(result, packet)

    def test_filter_drops(self):
        """Test filter() when a filter drops the packet."""
        pf = filter.PacketFilter()

        class Filter1:
            def filter(self, packet):
                return packet

        class Filter2:
            def filter(self, packet):
                return None  # Drops packet

        pf.register(Filter1)
        pf.register(Filter2)

        packet = fake.fake_packet()
        result = pf.filter(packet)

        self.assertIsNone(result)

    def test_filter_order(self):
        """Test filters are called in registration order."""
        pf = filter.PacketFilter()
        call_order = []

        class Filter1:
            def filter(self, packet):
                call_order.append('Filter1')
                return packet

        class Filter2:
            def filter(self, packet):
                call_order.append('Filter2')
                return packet

        class Filter3:
            def filter(self, packet):
                call_order.append('Filter3')
                return packet

        pf.register(Filter1)
        pf.register(Filter2)
        pf.register(Filter3)

        packet = fake.fake_packet()
        pf.filter(packet)

        self.assertEqual(call_order, ['Filter1', 'Filter2', 'Filter3'])

    def test_filter_stops_on_drop(self):
        """Test filter() stops processing when packet is dropped."""
        pf = filter.PacketFilter()
        call_order = []

        class Filter1:
            def filter(self, packet):
                call_order.append('Filter1')
                return packet

        class Filter2:
            def filter(self, packet):
                call_order.append('Filter2')
                return None  # Drops

        class Filter3:
            def filter(self, packet):
                call_order.append('Filter3')
                return packet

        pf.register(Filter1)
        pf.register(Filter2)
        pf.register(Filter3)

        packet = fake.fake_packet()
        result = pf.filter(packet)

        self.assertIsNone(result)
        # Filter3 should not be called
        self.assertEqual(call_order, ['Filter1', 'Filter2'])

    def test_filter_with_exception(self):
        """Test filter() handles exceptions gracefully."""
        pf = filter.PacketFilter()

        class FailingFilter:
            def filter(self, packet):
                raise Exception('Filter error')

        pf.register(FailingFilter)

        packet = fake.fake_packet()
        # Should not raise exception
        with mock.patch('aprsd.packets.filter.LOG') as mock_log:
            pf.filter(packet)
            mock_log.error.assert_called()

    def test_filter_empty(self):
        """Test filter() with no registered filters."""
        pf = filter.PacketFilter()
        packet = fake.fake_packet()

        result = pf.filter(packet)
        # When no filters, packet should pass through
        self.assertEqual(result, packet)

    def test_filter_typo_in_log(self):
        """Test that the typo in filter error logging doesn't break."""
        pf = filter.PacketFilter()

        class FailingFilter:
            def filter(self, packet):
                raise Exception('Filter error')

        pf.register(FailingFilter)

        packet = fake.fake_packet()
        # Should handle the typo gracefully (__clas__ instead of __class__)
        with mock.patch('aprsd.packets.filter.LOG') as mock_log:
            pf.filter(packet)
            # Should log error even with typo
            self.assertTrue(mock_log.error.called)
