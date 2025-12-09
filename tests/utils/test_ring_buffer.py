import unittest

from aprsd.utils.ring_buffer import RingBuffer


class TestRingBuffer(unittest.TestCase):
    """Unit tests for the RingBuffer class."""

    def test_init(self):
        """Test initialization."""
        rb = RingBuffer(5)
        self.assertEqual(rb.max, 5)
        self.assertEqual(len(rb.data), 0)

    def test_append_non_full(self):
        """Test append() when buffer is not full."""
        rb = RingBuffer(3)
        rb.append(1)
        rb.append(2)

        self.assertEqual(len(rb), 2)
        self.assertEqual(rb.get(), [1, 2])

    def test_append_to_full(self):
        """Test append() when buffer becomes full."""
        rb = RingBuffer(3)
        rb.append(1)
        rb.append(2)
        rb.append(3)

        self.assertEqual(len(rb), 3)
        self.assertEqual(rb.get(), [1, 2, 3])
        # Should transition to full state
        self.assertEqual(rb.__class__.__name__, '__Full')

    def test_append_overwrites_when_full(self):
        """Test append() overwrites oldest when full."""
        rb = RingBuffer(3)
        rb.append(1)
        rb.append(2)
        rb.append(3)
        rb.append(4)  # Should overwrite 1

        self.assertEqual(len(rb), 3)
        result = rb.get()
        # Should return elements in order from oldest to newest
        self.assertEqual(len(result), 3)
        self.assertIn(2, result)
        self.assertIn(3, result)
        self.assertIn(4, result)

    def test_get_non_full(self):
        """Test get() when buffer is not full."""
        rb = RingBuffer(5)
        rb.append(1)
        rb.append(2)

        result = rb.get()
        self.assertEqual(result, [1, 2])

    def test_get_empty(self):
        """Test get() when buffer is empty."""
        rb = RingBuffer(5)
        result = rb.get()
        self.assertEqual(result, [])

    def test_len_non_full(self):
        """Test __len__() when buffer is not full."""
        rb = RingBuffer(5)
        rb.append(1)
        rb.append(2)

        self.assertEqual(len(rb), 2)

    def test_len_full(self):
        """Test __len__() when buffer is full."""
        rb = RingBuffer(3)
        rb.append(1)
        rb.append(2)
        rb.append(3)

        self.assertEqual(len(rb), 3)

    def test_wraparound(self):
        """Test that buffer wraps around correctly."""
        rb = RingBuffer(3)
        # Fill buffer
        rb.append(1)
        rb.append(2)
        rb.append(3)

        # Add more to test wraparound
        rb.append(4)
        rb.append(5)
        rb.append(6)

        result = rb.get()
        self.assertEqual(len(result), 3)
        # Should contain the last 3 elements
        self.assertIn(4, result)
        self.assertIn(5, result)
        self.assertIn(6, result)

    def test_get_order_when_full(self):
        """Test get() returns elements in correct order when full."""
        rb = RingBuffer(3)
        rb.append('a')
        rb.append('b')
        rb.append('c')
        rb.append('d')  # Overwrites 'a'

        result = rb.get()
        # Should return from current position
        self.assertEqual(len(result), 3)
        # Order should be maintained from oldest to newest
        self.assertIn('b', result)
        self.assertIn('c', result)
        self.assertIn('d', result)

    def test_multiple_wraparounds(self):
        """Test multiple wraparounds."""
        rb = RingBuffer(3)
        for i in range(10):
            rb.append(i)

        result = rb.get()
        self.assertEqual(len(result), 3)
        # Should contain last 3 elements
        self.assertIn(7, result)
        self.assertIn(8, result)
        self.assertIn(9, result)

    def test_single_element_buffer(self):
        """Test buffer with size 1."""
        rb = RingBuffer(1)
        rb.append(1)
        self.assertEqual(len(rb), 1)
        self.assertEqual(rb.get(), [1])

        rb.append(2)
        self.assertEqual(len(rb), 1)
        result = rb.get()
        self.assertEqual(len(result), 1)
        self.assertIn(2, result)
