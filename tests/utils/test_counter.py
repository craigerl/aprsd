import threading
import unittest

from aprsd.utils.counter import PacketCounter


class TestPacketCounter(unittest.TestCase):
    """Unit tests for the PacketCounter class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance
        PacketCounter._instance = None

    def tearDown(self):
        """Clean up after tests."""
        PacketCounter._instance = None

    def test_singleton_pattern(self):
        """Test that PacketCounter is a singleton."""
        counter1 = PacketCounter()
        counter2 = PacketCounter()
        self.assertIs(counter1, counter2)

    def test_initial_value(self):
        """Test that counter is initialized with random value."""
        counter = PacketCounter()
        value = int(counter.value)
        self.assertGreaterEqual(value, 1)
        self.assertLessEqual(value, 9999)

    def test_increment(self):
        """Test increment() method."""
        counter = PacketCounter()
        initial_value = int(counter.value)
        counter.increment()
        new_value = int(counter.value)

        if initial_value == 9999:
            self.assertEqual(new_value, 1)
        else:
            self.assertEqual(new_value, initial_value + 1)

    def test_increment_wraps_around(self):
        """Test increment() wraps around at MAX_PACKET_ID."""
        counter = PacketCounter()
        counter._val = 9999
        counter.increment()
        self.assertEqual(int(counter.value), 1)

    def test_value_property(self):
        """Test value property returns string."""
        counter = PacketCounter()
        value = counter.value
        self.assertIsInstance(value, str)
        self.assertTrue(value.isdigit())

    def test_str(self):
        """Test __str__() method."""
        counter = PacketCounter()
        counter_str = str(counter)
        self.assertIsInstance(counter_str, str)
        self.assertTrue(counter_str.isdigit())

    def test_repr(self):
        """Test __repr__() method."""
        counter = PacketCounter()
        counter_repr = repr(counter)
        self.assertIsInstance(counter_repr, str)
        self.assertTrue(counter_repr.isdigit())

    def test_thread_safety(self):
        """Test that counter operations are thread-safe."""
        counter = PacketCounter()
        results = []
        errors = []

        def increment_multiple():
            try:
                for _ in range(100):
                    counter.increment()
                    results.append(int(counter.value))
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=increment_multiple) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have no errors
        self.assertEqual(len(errors), 0)

        # All values should be valid
        for value in results:
            self.assertGreaterEqual(value, 1)
            self.assertLessEqual(value, 9999)

        # Final value should be consistent
        final_value = int(counter.value)
        self.assertGreaterEqual(final_value, 1)
        self.assertLessEqual(final_value, 9999)

    def test_concurrent_access(self):
        """Test concurrent access to value property."""
        counter = PacketCounter()
        values = []

        def get_value():
            for _ in range(50):
                values.append(int(counter.value))

        threads = [threading.Thread(target=get_value) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All values should be valid
        for value in values:
            self.assertGreaterEqual(value, 1)
            self.assertLessEqual(value, 9999)
