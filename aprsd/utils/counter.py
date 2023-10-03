from multiprocessing import RawValue
import threading

import wrapt


class PacketCounter:
    """
    Global Packet id counter class.

    This is a singleton based class that keeps
    an incrementing counter for all packets to
    be sent.  All new Packet objects gets a new
    message id, which is the next number available
    from the PacketCounter.

    """

    _instance = None
    max_count = 9999
    lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Make this a singleton class."""
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance.val = RawValue("i", 1)
        return cls._instance

    @wrapt.synchronized(lock)
    def increment(self):
        if self.val.value == self.max_count:
            self.val.value = 1
        else:
            self.val.value += 1

    @property
    @wrapt.synchronized(lock)
    def value(self):
        return str(self.val.value)

    @wrapt.synchronized(lock)
    def __repr__(self):
        return str(self.val.value)

    @wrapt.synchronized(lock)
    def __str__(self):
        return str(self.val.value)
