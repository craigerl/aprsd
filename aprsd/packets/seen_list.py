import datetime
import logging

from oslo_config import cfg

from aprsd.packets import core
from aprsd.utils import objectstore


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class SeenList(objectstore.ObjectStoreMixin):
    """Global callsign seen list."""

    _instance = None
    data: dict = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.data = {}
        return cls._instance

    def stats(self, serializable=False):
        """Return the stats for the PacketTrack class."""
        with self.lock:
            return self.data

    def rx(self, packet: type[core.Packet]):
        """When we get a packet from the network, update the seen list."""
        with self.lock:
            callsign = None
            if packet.from_call:
                callsign = packet.from_call
            else:
                LOG.warning(f"Can't find FROM in packet {packet}")
                return
            if callsign not in self.data:
                self.data[callsign] = {
                    "last": None,
                    "count": 0,
                }
            self.data[callsign]["last"] = datetime.datetime.now()
            self.data[callsign]["count"] += 1

    def tx(self, packet: type[core.Packet]):
        """We don't care about TX packets."""
