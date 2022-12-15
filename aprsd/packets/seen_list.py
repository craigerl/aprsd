import datetime
import logging
import threading

import wrapt

from aprsd.utils import objectstore


LOG = logging.getLogger("APRSD")


class SeenList(objectstore.ObjectStoreMixin):
    """Global callsign seen list."""

    _instance = None
    lock = threading.Lock()
    data = {}
    config = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if "config" in kwargs:
                cls._instance.config = kwargs["config"]
                cls._instance._init_store()
            cls._instance.data = {}
        return cls._instance

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
        self.data[callsign]["last"] = str(datetime.datetime.now())
        self.data[callsign]["count"] += 1
