import datetime
import logging
import threading

from oslo_config import cfg
import wrapt

from aprsd.utils import objectstore


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class SeenList(objectstore.ObjectStoreMixin):
    """Global callsign seen list."""

    _instance = None
    lock = threading.Lock()
    data: dict = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_store()
            cls._instance.data = {}
        return cls._instance

    @wrapt.synchronized(lock)
    def stats(self, serializable=False):
        """Return the stats for the PacketTrack class."""
        return self.data

    @wrapt.synchronized(lock)
    def copy(self):
        """Return a copy of the data."""
        return self.data.copy()

    @wrapt.synchronized(lock)
    def update_seen(self, packet):
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
