from collections import OrderedDict
from collections.abc import MutableMapping
import logging
import threading

from oslo_config import cfg
import wrapt

from aprsd.packets import seen_list
from aprsd.utils import objectstore


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class PacketList(MutableMapping, objectstore.ObjectStoreMixin):
    _instance = None
    lock = threading.Lock()
    _total_rx: int = 0
    _total_tx: int = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._maxlen = 100
            cls.data = {
                "types": {},
                "packets": OrderedDict(),
            }
        return cls._instance

    @wrapt.synchronized(lock)
    def rx(self, packet):
        """Add a packet that was received."""
        self._total_rx += 1
        self._add(packet)
        ptype = packet.__class__.__name__
        if not ptype in self.data["types"]:
            self.data["types"][ptype] = {"tx": 0, "rx": 0}
        self.data["types"][ptype]["rx"] += 1
        seen_list.SeenList().update_seen(packet)

    @wrapt.synchronized(lock)
    def tx(self, packet):
        """Add a packet that was received."""
        self._total_tx += 1
        self._add(packet)
        ptype = packet.__class__.__name__
        if not ptype in self.data["types"]:
            self.data["types"][ptype] = {"tx": 0, "rx": 0}
        self.data["types"][ptype]["tx"] += 1
        seen_list.SeenList().update_seen(packet)

    @wrapt.synchronized(lock)
    def add(self, packet):
        self._add(packet)

    def _add(self, packet):
        self.data["packets"][packet.key] = packet

    def copy(self):
        return self.d.copy()

    @property
    def maxlen(self):
        return self._maxlen

    @wrapt.synchronized(lock)
    def find(self, packet):
        return self.get(packet.key)

    def __getitem__(self, key):
        # self.d.move_to_end(key)
        return self.data["packets"][key]

    def __setitem__(self, key, value):
        if key in self.data["packets"]:
            self.data["packets"].move_to_end(key)
        elif len(self.data["packets"]) == self.maxlen:
            self.data["packets"].popitem(last=False)
        self.data["packets"][key] = value

    def __delitem__(self, key):
        del self.data["packets"][key]

    def __iter__(self):
        return self.data["packets"].__iter__()

    def __len__(self):
        return len(self.data["packets"])

    @wrapt.synchronized(lock)
    def total_rx(self):
        return self._total_rx

    @wrapt.synchronized(lock)
    def total_tx(self):
        return self._total_tx

    def stats(self, serializable=False) -> dict:
        stats = {
            "total_tracked": self.total_tx() + self.total_rx(),
            "rx": self.total_rx(),
            "tx": self.total_tx(),
            "types": self.data["types"],
            "packets": self.data["packets"],
        }

        return stats
