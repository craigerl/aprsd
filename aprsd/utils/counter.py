import random
import threading

import wrapt


MAX_PACKET_ID = 9999


class PacketCounter:
    """
    Global Packet ID counter class.

    This is a singleton-based class that keeps
    an incrementing counter for all packets to
    be sent. All new Packet objects get a new
    message ID, which is the next number available
    from the PacketCounter.

    """

    _instance = None
    lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Make this a singleton class."""
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance._val = random.randint(1, MAX_PACKET_ID)  # Initialize counter
        return cls._instance

    @wrapt.synchronized(lock)
    def increment(self):
        """Increment the counter, reset if it exceeds MAX_PACKET_ID."""
        if self._val == MAX_PACKET_ID:
            self._val = 1
        else:
            self._val += 1

    @property
    @wrapt.synchronized(lock)
    def value(self):
        """Get the current value as a string."""
        return str(self._val)

    @wrapt.synchronized(lock)
    def __repr__(self):
        """String representation of the current value."""
        return str(self._val)

    @wrapt.synchronized(lock)
    def __str__(self):
        """String representation of the current value."""
        return str(self._val)
