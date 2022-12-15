from dataclasses import asdict, dataclass, field
import datetime
import logging
import threading
import time
# Due to a failure in python 3.8
from typing import List

import dacite
import wrapt

from aprsd import utils
from aprsd.utils import objectstore


LOG = logging.getLogger("APRSD")

PACKET_TYPE_MESSAGE = "message"
PACKET_TYPE_ACK = "ack"
PACKET_TYPE_MICE = "mic-e"
PACKET_TYPE_WX = "weather"
PACKET_TYPE_UNKNOWN = "unknown"
PACKET_TYPE_STATUS = "status"
PACKET_TYPE_BEACON = "beacon"
PACKET_TYPE_UNCOMPRESSED = "uncompressed"


@dataclass
class Packet:
    from_call: str
    to_call: str
    addresse: str = None
    format: str = None
    msgNo: str = None   # noqa: N815
    packet_type: str = None
    timestamp: float = field(default_factory=time.time)
    raw: str = None
    _raw_dict: dict = field(repr=True, default_factory=lambda: {})

    def get(self, key, default=None):
        """Emulate a getter on a dict."""
        if hasattr(self, key):
            return getattr(self, key)
        else:
            return default

    @staticmethod
    def factory(raw_packet):
        raw = raw_packet.copy()
        raw["_raw_dict"] = raw.copy()
        translate_fields = {
            "from": "from_call",
            "to": "to_call",
        }
        # First translate some fields
        for key in translate_fields:
            if key in raw:
                raw[translate_fields[key]] = raw[key]
                del raw[key]

        if "addresse" in raw:
            raw["to_call"] = raw["addresse"]

        packet_type = get_packet_type(raw)
        raw["packet_type"] = packet_type
        class_name = TYPE_LOOKUP[packet_type]
        if packet_type == PACKET_TYPE_UNKNOWN:
            # Try and figure it out here
            if "latitude" in raw:
                class_name = GPSPacket

        if packet_type == PACKET_TYPE_WX:
            # the weather information is in a dict
            # this brings those values out to the outer dict
            for key in raw["weather"]:
                raw[key] = raw["weather"][key]

        return dacite.from_dict(data_class=class_name, data=raw)

    def log(self, header=None):
        """LOG a packet to the logfile."""
        asdict(self)
        log_list = ["\n"]
        if header:
            log_list.append(f"{header} _______________")
        log_list.append(f"  Packet  : {self.__class__.__name__}")
        log_list.append(f"  Raw     : {self.raw}")
        if self.to_call:
            log_list.append(f"  To      : {self.to_call}")
        if self.from_call:
            log_list.append(f"  From    : {self.from_call}")
        if hasattr(self, "path"):
            log_list.append(f"  Path    : {'=>'.join(self.path)}")
        if hasattr(self, "via"):
            log_list.append(f"  VIA     : {self.via}")

        elif isinstance(self, MessagePacket):
            log_list.append(f"  Message : {self.message_text}")

        if self.msgNo:
            log_list.append(f"  Msg #   : {self.msgNo}")
        log_list.append(f"{header} _______________ Complete")

        LOG.info("\n".join(log_list))
        LOG.debug(self)


@dataclass
class PathPacket(Packet):
    path: List[str] = field(default_factory=list)
    via: str = None


@dataclass
class AckPacket(PathPacket):
    response: str = None


@dataclass
class MessagePacket(PathPacket):
    message_text: str = None


@dataclass
class StatusPacket(PathPacket):
    status: str = None
    timestamp: int = 0
    messagecapable: bool = False
    comment: str = None


@dataclass
class GPSPacket(PathPacket):
    latitude: float = 0.00
    longitude: float = 0.00
    altitude: float = 0.00
    rng: float = 0.00
    posambiguity: int = 0
    timestamp: int = 0
    comment: str = None
    symbol: str = None
    symbol_table: str = None
    speed: float = 0.00
    course: int = 0


@dataclass
class MicEPacket(GPSPacket):
    messagecapable: bool = False
    mbits: str = None
    mtype: str = None


@dataclass
class WeatherPacket(GPSPacket):
    symbol: str = "_"
    wind_gust: float = 0.00
    temperature: float = 0.00
    rain_1h: float = 0.00
    rain_24h: float = 0.00
    rain_since_midnight: float = 0.00
    humidity: int = 0
    pressure: float = 0.00
    comment: str = None


class PacketList:
    """Class to track all of the packets rx'd and tx'd by aprsd."""

    _instance = None
    lock = threading.Lock()
    config = None

    packet_list = {}

    total_recv = 0
    total_tx = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.packet_list = utils.RingBuffer(1000)
            cls._instance.config = kwargs["config"]
        return cls._instance

    def __init__(self, config=None):
        if config:
            self.config = config

    @wrapt.synchronized(lock)
    def __iter__(self):
        return iter(self.packet_list)

    @wrapt.synchronized(lock)
    def add(self, packet: Packet):
        packet.ts = time.time()
        if (packet.from_call == self.config["aprs"]["login"]):
            self.total_tx += 1
        else:
            self.total_recv += 1
        self.packet_list.append(packet)
        SeenList().update_seen(packet)

    @wrapt.synchronized(lock)
    def get(self):
        return self.packet_list.get()

    @wrapt.synchronized(lock)
    def total_received(self):
        return self.total_recv

    @wrapt.synchronized(lock)
    def total_sent(self):
        return self.total_tx


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
    def update_seen(self, packet: Packet):
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


TYPE_LOOKUP = {
    PACKET_TYPE_WX: WeatherPacket,
    PACKET_TYPE_MESSAGE: MessagePacket,
    PACKET_TYPE_ACK: AckPacket,
    PACKET_TYPE_MICE: MicEPacket,
    PACKET_TYPE_STATUS: StatusPacket,
    PACKET_TYPE_BEACON: GPSPacket,
    PACKET_TYPE_UNKNOWN: Packet,
}


def get_packet_type(packet: dict):
    """Decode the packet type from the packet."""

    format = packet.get("format", None)
    msg_response = packet.get("response", None)
    packet_type = "unknown"
    if format == "message" and msg_response == "ack":
        packet_type = PACKET_TYPE_ACK
    elif format == "message":
        packet_type = PACKET_TYPE_MESSAGE
    elif format == "mic-e":
        packet_type = PACKET_TYPE_MICE
    elif format == "status":
        packet_type = PACKET_TYPE_STATUS
    elif format == PACKET_TYPE_BEACON:
        packet_type = PACKET_TYPE_BEACON
    elif format == PACKET_TYPE_UNCOMPRESSED:
        if packet.get("symbol", None) == "_":
            packet_type = PACKET_TYPE_WX
    return packet_type


def is_message_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_MESSAGE


def is_ack_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_ACK


def is_mice_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_MICE
