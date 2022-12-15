import datetime
import logging
import threading

import wrapt

from aprsd import utils
from aprsd.utils import objectstore


LOG = logging.getLogger("APRSD")


class WatchList(objectstore.ObjectStoreMixin):
    """Global watch list and info for callsigns."""

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

    def __init__(self, config=None):
        if config:
            self.config = config

            ring_size = config["aprsd"]["watch_list"].get("packet_keep_count", 10)

            for callsign in config["aprsd"]["watch_list"].get("callsigns", []):
                call = callsign.replace("*", "")
                # FIXME(waboring) - we should fetch the last time we saw
                # a beacon from a callsign or some other mechanism to find
                # last time a message was seen by aprs-is.  For now this
                # is all we can do.
                self.data[call] = {
                    "last": datetime.datetime.now(),
                    "packets": utils.RingBuffer(
                        ring_size,
                    ),
                }

    def is_enabled(self):
        if self.config and "watch_list" in self.config["aprsd"]:
            return self.config["aprsd"]["watch_list"].get("enabled", False)
        else:
            return False

    def callsign_in_watchlist(self, callsign):
        return callsign in self.data

    @wrapt.synchronized(lock)
    def update_seen(self, packet):
        if packet.addresse:
            callsign = packet.addresse
        else:
            callsign = packet.from_call
        if self.callsign_in_watchlist(callsign):
            self.data[callsign]["last"] = datetime.datetime.now()
            self.data[callsign]["packets"].append(packet)

    def last_seen(self, callsign):
        if self.callsign_in_watchlist(callsign):
            return self.data[callsign]["last"]

    def age(self, callsign):
        now = datetime.datetime.now()
        return str(now - self.last_seen(callsign))

    def max_delta(self, seconds=None):
        watch_list_conf = self.config["aprsd"]["watch_list"]
        if not seconds:
            seconds = watch_list_conf["alert_time_seconds"]
        max_timeout = {"seconds": seconds}
        return datetime.timedelta(**max_timeout)

    def is_old(self, callsign, seconds=None):
        """Watch list callsign last seen is old compared to now?

        This tests to see if the last time we saw a callsign packet,
        if that is older than the allowed timeout in the config.

        We put this here so any notification plugin can use this
        same test.
        """
        age = self.age(callsign)

        delta = utils.parse_delta_str(age)
        d = datetime.timedelta(**delta)

        max_delta = self.max_delta(seconds=seconds)

        if d > max_delta:
            return True
        else:
            return False
