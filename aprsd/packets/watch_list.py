import datetime
import logging

from oslo_config import cfg

from aprsd import utils
from aprsd.packets import core
from aprsd.utils import objectstore


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class WatchList(objectstore.ObjectStoreMixin):
    """Global watch list and info for callsigns."""

    _instance = None
    data = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self._update_from_conf()

    def _update_from_conf(self, config=None):
        with self.lock:
            if CONF.watch_list.enabled and CONF.watch_list.callsigns:
                for callsign in CONF.watch_list.callsigns:
                    call = callsign.replace("*", "")
                    # FIXME(waboring) - we should fetch the last time we saw
                    # a beacon from a callsign or some other mechanism to find
                    # last time a message was seen by aprs-is.  For now this
                    # is all we can do.
                    if call not in self.data:
                        self.data[call] = {
                            "last": None,
                            "packet": None,
                        }

    def stats(self, serializable=False) -> dict:
        stats = {}
        with self.lock:
            for callsign in self.data:
                stats[callsign] = {
                    "last": self.data[callsign]["last"],
                    "packet": self.data[callsign]["packet"],
                    "age": self.age(callsign),
                    "old": self.is_old(callsign),
                }
        return stats

    def is_enabled(self):
        return CONF.watch_list.enabled

    def callsign_in_watchlist(self, callsign):
        with self.lock:
            return callsign in self.data

    def rx(self, packet: type[core.Packet]) -> None:
        """Track when we got a packet from the network."""
        callsign = packet.from_call

        if self.callsign_in_watchlist(callsign):
            with self.lock:
                self.data[callsign]["last"] = datetime.datetime.now()
                self.data[callsign]["packet"] = packet

    def tx(self, packet: type[core.Packet]) -> None:
        """We don't care about TX packets."""

    def last_seen(self, callsign):
        with self.lock:
            if self.callsign_in_watchlist(callsign):
                return self.data[callsign]["last"]

    def age(self, callsign):
        now = datetime.datetime.now()
        last_seen_time = self.last_seen(callsign)
        if last_seen_time:
            return str(now - last_seen_time)
        else:
            return None

    def max_delta(self, seconds=None):
        if not seconds:
            seconds = CONF.watch_list.alert_time_seconds
        max_timeout = {"seconds": seconds}
        return datetime.timedelta(**max_timeout)

    def is_old(self, callsign, seconds=None):
        """Watch list callsign last seen is old compared to now?

        This tests to see if the last time we saw a callsign packet,
        if that is older than the allowed timeout in the config.

        We put this here so any notification plugin can use this
        same test.
        """
        if not self.callsign_in_watchlist(callsign):
            return False

        age = self.age(callsign)
        if age:
            delta = utils.parse_delta_str(age)
            d = datetime.timedelta(**delta)

            max_delta = self.max_delta(seconds=seconds)

            if d > max_delta:
                return True
            else:
                return False
        else:
            return False
