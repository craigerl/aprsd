import unittest

from aprsd.utils.ring_buffer import RingBuffer


class TestRingBufferClassSwap(unittest.TestCase):
    """Guard against the old __class__ swap implementation.

    The old RingBuffer permanently replaced the instance's __class__
    with a nested __Full class once the buffer filled.  That is fragile:
    it mutates the instance type at runtime and breaks isinstance() /
    subclass checks.  This rewrite must behave identically for the
    public API (append/get/len) without swapping the class.
    """

    def test_class_does_not_change_when_full(self):
        """The instance's class must not change once the buffer fills."""
        rb = RingBuffer(3)
        cls_before = type(rb)
        rb.append(1)
        rb.append(2)
        rb.append(3)
        rb.append(4)  # would trigger the old __Full swap
        self.assertIs(type(rb), cls_before)

    def test_isinstance_still_works(self):
        """isinstance() must still hold after the buffer fills."""
        rb = RingBuffer(3)
        for i in range(10):
            rb.append(i)
        self.assertIsInstance(rb, RingBuffer)

    def test_behavior_unchanged(self):
        """append/get/len behavior must match the old semantics."""
        rb = RingBuffer(3)
        for i in range(6):
            rb.append(i)
        self.assertEqual(len(rb), 3)
        self.assertEqual(rb.get(), [3, 4, 5])
