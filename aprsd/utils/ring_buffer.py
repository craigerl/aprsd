from collections import deque


class RingBuffer:
    """A fixed-size ring buffer backed by a bounded deque.

    Appending past the size limit silently overwrites the oldest
    element.  A size_max <= 0 behaves like an unbounded list (nothing
    is ever overwritten).

    Previously this class swapped the instance's __class__ to a nested
    __Full class once the buffer filled, which mutated the runtime type
    and broke isinstance()/subclass checks.  The bounded deque gives the
    same append/get/len semantics without the class swap.
    """

    max: int = 100

    def __init__(self, size_max):
        self.max = size_max
        self.data: deque = deque(maxlen=size_max if size_max > 0 else None)

    def append(self, x):
        """Append an element, overwriting the oldest when full."""
        self.data.append(x)

    def get(self):
        """Return a list of elements from the oldest to the newest."""
        return list(self.data)

    def __len__(self):
        return len(self.data)
