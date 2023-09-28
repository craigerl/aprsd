from collections import MutableMapping, OrderedDict
import logging
import threading

from oslo_config import cfg
import wrapt

from aprsd import stats
from aprsd.packets import seen_list


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class PacketList(MutableMapping):
    _instance = None
    lock = threading.Lock()
    _total_rx: int = 0
    _total_tx: int = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._maxlen = 1000
            cls.d = OrderedDict()
        return cls._instance

    @wrapt.synchronized(lock)
    def rx(self, packet):
        """Add a packet that was received."""
        self._total_rx += 1
        self._add(packet)
        seen_list.SeenList().update_seen(packet)
        stats.APRSDStats().rx(packet)

    @wrapt.synchronized(lock)
    def tx(self, packet):
        """Add a packet that was received."""
        self._total_tx += 1
        self._add(packet)
        seen_list.SeenList().update_seen(packet)
        stats.APRSDStats().tx(packet)

    @wrapt.synchronized(lock)
    def add(self, packet):
        self._add(packet)

    def _add(self, packet):
        key = packet.key()
        self[key] = packet

    @property
    def maxlen(self):
        return self._maxlen

    @wrapt.synchronized(lock)
    def find(self, packet):
        key = packet.key()
        return self.get(key)

    def __getitem__(self, key):
        #self.d.move_to_end(key)
        return self.d[key]

    def __setitem__(self, key, value):
        if key in self.d:
            self.d.move_to_end(key)
        elif len(self.d) == self.maxlen:
            self.d.popitem(last=False)
        self.d[key] = value

    def __delitem__(self, key):
        del self.d[key]

    def __iter__(self):
        return self.d.__iter__()

    def __len__(self):
        return len(self.d)

    @wrapt.synchronized(lock)
    def total_rx(self):
        return self._total_rx

    @wrapt.synchronized(lock)
    def total_tx(self):
        return self._total_tx
