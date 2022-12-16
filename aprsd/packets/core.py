import abc
from dataclasses import asdict, dataclass, field
import logging
import re
import time
# Due to a failure in python 3.8
from typing import List

import dacite

from aprsd import client, stats
from aprsd.threads import tx
from aprsd.utils import counter


LOG = logging.getLogger("APRSD")

PACKET_TYPE_MESSAGE = "message"
PACKET_TYPE_ACK = "ack"
PACKET_TYPE_MICE = "mic-e"
PACKET_TYPE_WX = "weather"
PACKET_TYPE_UNKNOWN = "unknown"
PACKET_TYPE_STATUS = "status"
PACKET_TYPE_BEACON = "beacon"
PACKET_TYPE_UNCOMPRESSED = "uncompressed"


@dataclass()
class Packet(metaclass=abc.ABCMeta):
    from_call: str
    to_call: str
    addresse: str = None
    format: str = None
    msgNo: str = None   # noqa: N815
    packet_type: str = None
    timestamp: float = field(default_factory=time.time)
    raw: str = None
    _raw_dict: dict = field(repr=False, default_factory=lambda: {})
    _retry_count = 3
    _last_send_time = 0
    _last_send_attempt = 0
    # Do we allow this packet to be saved to send later?
    _allow_delay = True

    _transport = None
    _raw_message = None

    def get(self, key, default=None):
        """Emulate a getter on a dict."""
        if hasattr(self, key):
            return getattr(self, key)
        else:
            return default

    def _init_for_send(self):
        """Do stuff here that is needed prior to sending over the air."""
        if not self.msgNo:
            c = counter.PacketCounter()
            c.increment()
            self.msgNo = c.value

        # now build the raw message for sending
        self._build_raw()

    def _build_raw(self):
        """Build the self.raw string which is what is sent over the air."""
        self.raw = self._filter_for_send().rstrip("\n")

    @staticmethod
    def factory(raw_packet):
        raw = raw_packet
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
            if isinstance(self, AckPacket):
                log_list.append(
                    f"{header} ___________"
                    f"(TX:{self._send_count} of {self._retry_count})",
                )
            else:
                log_list.append(f"{header} _______________")
        log_list.append(f"  Packet  : {self.__class__.__name__}")
        log_list.append(f"  Raw     : {self.raw}")
        if self.to_call:
            log_list.append(f"  To      : {self.to_call}")
        if self.from_call:
            log_list.append(f"  From    : {self.from_call}")
        if hasattr(self, "path") and self.path:
            log_list.append(f"  Path    : {'=>'.join(self.path)}")
        if hasattr(self, "via") and self.via:
            log_list.append(f"  VIA     : {self.via}")

        elif isinstance(self, MessagePacket):
            log_list.append(f"  Message : {self.message_text}")

        if hasattr(self, "comment") and self.comment:
            log_list.append(f"  Comment : {self.comment}")

        if self.msgNo:
            log_list.append(f"  Msg #   : {self.msgNo}")
        log_list.append(f"{header} _______________ Complete")

        LOG.info("\n".join(log_list))
        LOG.debug(self)

    def _filter_for_send(self) -> str:
        """Filter and format message string for FCC."""
        # max?  ftm400 displays 64, raw msg shows 74
        # and ftm400-send is max 64.  setting this to
        # 67 displays 64 on the ftm400. (+3 {01 suffix)
        # feature req: break long ones into two msgs
        message = self.raw[:67]
        # We all miss George Carlin
        return re.sub("fuck|shit|cunt|piss|cock|bitch", "****", message)

    def send(self):
        """Method to send a packet."""
        self._init_for_send()
        thread = tx.SendPacketThread(packet=self)
        thread.start()

    def send_direct(self, aprsis_client=None):
        """Send the message in the same thread as caller."""
        self._init_for_send()
        if aprsis_client:
            cl = aprsis_client
        else:
            cl = client.factory.create().client
        self.log(header="Sending Message Direct")
        cl.send(self.raw)
        stats.APRSDStats().msgs_tx_inc()


@dataclass()
class PathPacket(Packet):
    path: List[str] = field(default_factory=list)
    via: str = None

    def _build_raw(self):
        raise NotImplementedError


@dataclass()
class AckPacket(PathPacket):
    response: str = None
    _send_count = 1

    def _build_raw(self):
        """Build the self.raw which is what is sent over the air."""
        self.raw = "{}>APZ100::{}:ack{}".format(
            self.from_call,
            self.to_call.ljust(9),
            self.msgNo,
        )

    def send(self):
        """Method to send a packet."""
        self._init_for_send()
        thread = tx.SendAckThread(packet=self)
        LOG.warning(f"Starting thread to TXACK {self}")
        thread.start()


@dataclass()
class MessagePacket(PathPacket):
    message_text: str = None

    def _filter_for_send(self) -> str:
        """Filter and format message string for FCC."""
        # max?  ftm400 displays 64, raw msg shows 74
        # and ftm400-send is max 64.  setting this to
        # 67 displays 64 on the ftm400. (+3 {01 suffix)
        # feature req: break long ones into two msgs
        message = self.message_text[:67]
        # We all miss George Carlin
        return re.sub("fuck|shit|cunt|piss|cock|bitch", "****", message)

    def _build_raw(self):
        """Build the self.raw which is what is sent over the air."""
        self.raw = "{}>APZ100::{}:{}{{{}".format(
            self.from_call,
            self.to_call.ljust(9),
            self._filter_for_send().rstrip("\n"),
            str(self.msgNo),
        )


@dataclass()
class StatusPacket(PathPacket):
    status: str = None
    timestamp: int = 0
    messagecapable: bool = False
    comment: str = None

    def _build_raw(self):
        raise NotImplementedError


@dataclass()
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

    def _build_raw(self):
        raise NotImplementedError


@dataclass()
class MicEPacket(GPSPacket):
    messagecapable: bool = False
    mbits: str = None
    mtype: str = None

    def _build_raw(self):
        raise NotImplementedError


@dataclass()
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

    def _build_raw(self):
        raise NotImplementedError


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

    pkt_format = packet.get("format", None)
    msg_response = packet.get("response", None)
    packet_type = "unknown"
    if pkt_format == "message" and msg_response == "ack":
        packet_type = PACKET_TYPE_ACK
    elif pkt_format == "message":
        packet_type = PACKET_TYPE_MESSAGE
    elif pkt_format == "mic-e":
        packet_type = PACKET_TYPE_MICE
    elif pkt_format == "status":
        packet_type = PACKET_TYPE_STATUS
    elif pkt_format == PACKET_TYPE_BEACON:
        packet_type = PACKET_TYPE_BEACON
    elif pkt_format == PACKET_TYPE_UNCOMPRESSED:
        if packet.get("symbol", None) == "_":
            packet_type = PACKET_TYPE_WX
    return packet_type


def is_message_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_MESSAGE


def is_ack_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_ACK


def is_mice_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_MICE
