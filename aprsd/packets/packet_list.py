from collections import OrderedDict
import logging
import threading

from oslo_config import cfg
import wrapt

from aprsd.packets import collector, core
from aprsd.utils import objectstore


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class PacketList(objectstore.ObjectStoreMixin):
    """Class to keep track of the packets we tx/rx."""
    _instance = None
    lock = threading.Lock()
    _total_rx: int = 0
    _total_tx: int = 0
    maxlen: int = 100

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.maxlen = CONF.packet_list_maxlen
            cls._instance._init_data()
        return cls._instance

    def _init_data(self):
        self.data = {
            "types": {},
            "packets": OrderedDict(),
        }

    @wrapt.synchronized(lock)
    def rx(self, packet: type[core.Packet]):
        """Add a packet that was received."""
        self._total_rx += 1
        self._add(packet)
        ptype = packet.__class__.__name__
        if not ptype in self.data["types"]:
            self.data["types"][ptype] = {"tx": 0, "rx": 0}
        self.data["types"][ptype]["rx"] += 1

    @wrapt.synchronized(lock)
    def tx(self, packet: type[core.Packet]):
        """Add a packet that was received."""
        self._total_tx += 1
        self._add(packet)
        ptype = packet.__class__.__name__
        if not ptype in self.data["types"]:
            self.data["types"][ptype] = {"tx": 0, "rx": 0}
        self.data["types"][ptype]["tx"] += 1

    @wrapt.synchronized(lock)
    def add(self, packet):
        self._add(packet)

    def _add(self, packet):
        if not self.data.get("packets"):
            self._init_data()
        if packet.key in self.data["packets"]:
            self.data["packets"].move_to_end(packet.key)
        elif len(self.data["packets"]) == self.maxlen:
            self.data["packets"].popitem(last=False)
        self.data["packets"][packet.key] = packet

    @wrapt.synchronized(lock)
    def copy(self):
        return self.data.copy()

    @wrapt.synchronized(lock)
    def find(self, packet):
        return self.data["packets"][packet.key]

    @wrapt.synchronized(lock)
    def __len__(self):
        return len(self.data["packets"])

    @wrapt.synchronized(lock)
    def total_rx(self):
        return self._total_rx

    @wrapt.synchronized(lock)
    def total_tx(self):
        return self._total_tx

    @wrapt.synchronized(lock)
    def stats(self, serializable=False) -> dict:
        # limit the number of packets to return to 50
        tmp = OrderedDict(
            reversed(
                list(
                    self.data.get("packets", OrderedDict()).items(),
                ),
            ),
        )
        pkts = []
        count = 1
        for packet in tmp:
            pkts.append(tmp[packet])
            count += 1
            if count > CONF.packet_list_stats_maxlen:
                break

        stats = {
            "total_tracked": self._total_rx + self._total_rx,
            "rx": self._total_rx,
            "tx": self._total_tx,
            "types": self.data.get("types", []),
            "packet_count": len(self.data.get("packets", [])),
            "maxlen": self.maxlen,
            "packets": pkts,
        }
        return stats


# Now register the PacketList with the collector
# every packet we RX and TX goes through the collector
# for processing for whatever reason is needed.
collector.PacketCollector().register(PacketList)
