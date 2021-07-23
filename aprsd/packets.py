import datetime
import logging
import threading
import time

from aprsd import utils

LOG = logging.getLogger("APRSD")

PACKET_TYPE_MESSAGE = "message"
PACKET_TYPE_ACK = "ack"
PACKET_TYPE_MICE = "mic-e"


class PacketList:
    """Class to track all of the packets rx'd and tx'd by aprsd."""

    _instance = None
    config = None

    packet_list = {}

    total_recv = 0
    total_tx = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.packet_list = utils.RingBuffer(100)
            cls._instance.lock = threading.Lock()
        return cls._instance

    def __init__(self, config=None):
        if config:
            self.config = config

    def __iter__(self):
        with self.lock:
            return iter(self.packet_list)

    def add(self, packet):
        with self.lock:
            packet["ts"] = time.time()
            if "from" in packet and packet["from"] == self.config["aprs"]["login"]:
                self.total_tx += 1
            else:
                self.total_recv += 1
            self.packet_list.append(packet)

    def get(self):
        with self.lock:
            return self.packet_list.get()

    def total_received(self):
        return self.total_recv

    def total_sent(self):
        return self.total_tx


class WatchList:
    """Global watch list and info for callsigns."""

    _instance = None
    callsigns = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.lock = threading.Lock()
            cls.callsigns = {}
        return cls._instance

    def __init__(self, config=None):
        if config:
            self.config = config

            ring_size = config["aprsd"]["watch_list"]["packet_keep_count"]

            for callsign in config["aprsd"]["watch_list"].get("callsigns", []):
                call = callsign.replace("*", "")
                # FIXME(waboring) - we should fetch the last time we saw
                # a beacon from a callsign or some other mechanism to find
                # last time a message was seen by aprs-is.  For now this
                # is all we can do.
                self.callsigns[call] = {
                    "last": datetime.datetime.now(),
                    "packets": utils.RingBuffer(
                        ring_size,
                    ),
                }

    def is_enabled(self):
        if "watch_list" in self.config["aprsd"]:
            return self.config["aprsd"]["watch_list"].get("enabled", False)
        else:
            return False

    def callsign_in_watchlist(self, callsign):
        return callsign in self.callsigns

    def update_seen(self, packet):
        callsign = packet["from"]
        if self.callsign_in_watchlist(callsign):
            self.callsigns[callsign]["last"] = datetime.datetime.now()
            self.callsigns[callsign]["packets"].append(packet)

    def last_seen(self, callsign):
        if self.callsign_in_watchlist(callsign):
            return self.callsigns[callsign]["last"]

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


def get_packet_type(packet):
    """Decode the packet type from the packet."""

    msg_format = packet.get("format", None)
    msg_response = packet.get("response", None)
    packet_type = "unknown"
    if msg_format == "message":
        packet_type = PACKET_TYPE_MESSAGE
    elif msg_response == "ack":
        packet_type = PACKET_TYPE_ACK
    elif msg_format == "mic-e":
        packet_type = PACKET_TYPE_MICE
    return packet_type
