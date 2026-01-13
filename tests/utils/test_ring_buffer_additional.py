import unittest

from aprsd.utils.ring_buffer import RingBuffer


class TestRingBufferAdditional(unittest.TestCase):
    """Additional unit tests for the RingBuffer class to cover edge cases."""

    def test_empty_buffer(self):
        """Test behavior with empty buffer."""
        rb = RingBuffer(5)
        self.assertEqual(len(rb), 0)
        self.assertEqual(rb.get(), [])

    def test_buffer_with_zero_size(self):
        """Test buffer with zero size."""
        rb = RingBuffer(0)
        # Should not crash, but behavior might be different
        # In this implementation, it will behave like a normal list
        rb.append(1)
        self.assertEqual(len(rb), 1)
        self.assertEqual(rb.get(), [1])

    def test_buffer_with_negative_size(self):
        """Test buffer with negative size."""
        # This might not be a valid use case, but let's test it
        rb = RingBuffer(-1)
        rb.append(1)
        self.assertEqual(len(rb), 1)
        self.assertEqual(rb.get(), [1])

    def test_append_none_value(self):
        """Test appending None values."""
        rb = RingBuffer(3)
        rb.append(None)
        rb.append(1)
        rb.append(2)

        result = rb.get()
        self.assertEqual(len(result), 3)
        self.assertIsNone(result[0])
        self.assertEqual(result[1], 1)
        self.assertEqual(result[2], 2)

    def test_append_multiple_types(self):
        """Test appending multiple different types of values."""
        rb = RingBuffer(4)
        rb.append('string')
        rb.append(42)
        rb.append([1, 2, 3])
        rb.append({'key': 'value'})

        result = rb.get()
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0], 'string')
        self.assertEqual(result[1], 42)
        self.assertEqual(result[2], [1, 2, 3])
        self.assertEqual(result[3], {'key': 'value'})

    def test_multiple_appends_then_get(self):
        """Test multiple appends followed by get operations."""
        rb = RingBuffer(5)

        # Append multiple items
        for i in range(10):
            rb.append(i)

        # Get should return the last 5 items
        result = rb.get()
        self.assertEqual(len(result), 5)
        self.assertEqual(result, [5, 6, 7, 8, 9])

    def test_get_returns_copy(self):
        """Test that get() returns a copy, not a reference."""
        rb = RingBuffer(3)
        rb.append(1)
        rb.append(2)
        rb.append(3)

        result = rb.get()
        # Modify the returned list
        result.append(4)

        # Original buffer should not be affected
        original = rb.get()
        self.assertEqual(len(original), 3)
        self.assertNotIn(4, original)

    def test_buffer_size_one(self):
        """Test buffer with size 1."""
        rb = RingBuffer(1)
        rb.append(1)
        self.assertEqual(len(rb), 1)
        self.assertEqual(rb.get(), [1])

        rb.append(2)
        self.assertEqual(len(rb), 1)
        result = rb.get()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], 2)

    def test_buffer_size_two(self):
        """Test buffer with size 2."""
        rb = RingBuffer(2)
        rb.append(1)
        rb.append(2)
        self.assertEqual(len(rb), 2)
        self.assertEqual(rb.get(), [1, 2])

        rb.append(3)
        self.assertEqual(len(rb), 2)
        result = rb.get()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 2)
        self.assertEqual(result[1], 3)

    def test_large_buffer_size(self):
        """Test with a large buffer size."""
        rb = RingBuffer(1000)
        for i in range(1000):
            rb.append(i)

        result = rb.get()
        self.assertEqual(len(result), 1000)
        self.assertEqual(result[0], 0)
        self.assertEqual(result[-1], 999)

    def test_buffer_with_many_wraparounds(self):
        """Test buffer with many wraparounds."""
        rb = RingBuffer(3)
        # Fill and wrap multiple times
        for i in range(100):
            rb.append(i)

        result = rb.get()
        self.assertEqual(len(result), 3)
        # Should contain the last 3 elements
        self.assertEqual(result[0], 97)
        self.assertEqual(result[1], 98)
        self.assertEqual(result[2], 99)

    def test_multiple_get_calls(self):
        """Test multiple get() calls return consistent results."""
        rb = RingBuffer(3)
        rb.append(1)
        rb.append(2)
        rb.append(3)

        result1 = rb.get()
        result2 = rb.get()
        result3 = rb.get()

        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)
        self.assertEqual(result1, [1, 2, 3])

    def test_get_order_consistency(self):
        """Test that get() maintains order consistency."""
        rb = RingBuffer(5)
        # Add elements
        elements = [1, 2, 3, 4, 5, 6, 7]
        for elem in elements:
            rb.append(elem)

        result = rb.get()
        # Should contain the last 5 elements in correct order
        self.assertEqual(len(result), 5)
        self.assertEqual(result, [3, 4, 5, 6, 7])


if __name__ == '__main__':
    unittest.main()
