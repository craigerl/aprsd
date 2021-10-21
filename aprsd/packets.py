import datetime
import logging
import threading
import time

from aprsd import objectstore, utils


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
            cls._instance.packet_list = utils.RingBuffer(1000)
            cls._instance.lock = threading.Lock()
            cls._instance.config = kwargs["config"]
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
            if (
                "fromcall" in packet
                and packet["fromcall"] == self.config["aprs"]["login"]
            ):
                self.total_tx += 1
            else:
                self.total_recv += 1
            self.packet_list.append(packet)
            SeenList().update_seen(packet)

    def get(self):
        with self.lock:
            return self.packet_list.get()

    def total_received(self):
        with self.lock:
            return self.total_recv

    def total_sent(self):
        with self.lock:
            return self.total_tx


class WatchList(objectstore.ObjectStoreMixin):
    """Global watch list and info for callsigns."""

    _instance = None
    data = {}
    config = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.lock = threading.Lock()
            cls._instance.config = kwargs["config"]
            cls._instance.data = {}
            cls._instance._init_store()
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

    def update_seen(self, packet):
        with self.lock:
            callsign = packet["from"]
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


class SeenList(objectstore.ObjectStoreMixin):
    """Global callsign seen list."""

    _instance = None
    data = {}
    config = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.lock = threading.Lock()
            cls._instance.config = kwargs["config"]
            cls._instance.data = {}
            cls._instance._init_store()
        return cls._instance

    def update_seen(self, packet):
        callsign = None
        if "fromcall" in packet:
            callsign = packet["fromcall"]
        elif "from" in packet:
            callsign = packet["from"]
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


def is_message_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_MESSAGE


def is_ack_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_ACK


def is_mice_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_MICE
