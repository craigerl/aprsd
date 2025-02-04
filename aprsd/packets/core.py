import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

# Due to a failure in python 3.8
from typing import Any, List, Optional, Type, TypeVar, Union

from aprslib import util as aprslib_util
from dataclasses_json import (
    CatchAll,
    DataClassJsonMixin,
    Undefined,
    dataclass_json,
)
from loguru import logger

from aprsd.utils import counter

# For mypy to be happy
A = TypeVar("A", bound="DataClassJsonMixin")
Json = Union[dict, list, str, int, float, bool, None]

LOG = logging.getLogger()
LOGU = logger

PACKET_TYPE_BULLETIN = "bulletin"
PACKET_TYPE_MESSAGE = "message"
PACKET_TYPE_ACK = "ack"
PACKET_TYPE_REJECT = "reject"
PACKET_TYPE_MICE = "mic-e"
PACKET_TYPE_WX = "wx"
PACKET_TYPE_WEATHER = "weather"
PACKET_TYPE_OBJECT = "object"
PACKET_TYPE_UNKNOWN = "unknown"
PACKET_TYPE_STATUS = "status"
PACKET_TYPE_BEACON = "beacon"
PACKET_TYPE_THIRDPARTY = "thirdparty"
PACKET_TYPE_TELEMETRY = "telemetry-message"
PACKET_TYPE_UNCOMPRESSED = "uncompressed"

NO_DATE = datetime(1900, 10, 24)


def _init_timestamp():
    """Build a unix style timestamp integer"""
    return int(round(time.time()))


def _init_send_time():
    # We have to use a datetime here, or the json encoder
    # Fails on a NoneType.
    return NO_DATE


def _init_msgNo():  # noqa: N802
    """For some reason __post__init doesn't get called.

    So in order to initialize the msgNo field in the packet
    we use this workaround.
    """
    c = counter.PacketCounter()
    c.increment()
    return c.value


def _translate_fields(raw: dict) -> dict:
    # Direct key checks instead of iteration
    if "from" in raw:
        raw["from_call"] = raw.pop("from")
    if "to" in raw:
        raw["to_call"] = raw.pop("to")

    # addresse overrides to_call
    if "addresse" in raw:
        raw["to_call"] = raw["addresse"]

    return raw


@dataclass_json
@dataclass(unsafe_hash=True)
class Packet:
    _type: str = field(default="Packet", hash=False)
    from_call: Optional[str] = field(default=None)
    to_call: Optional[str] = field(default=None)
    addresse: Optional[str] = field(default=None)
    format: Optional[str] = field(default=None)
    msgNo: Optional[str] = field(default=None)  # noqa: N815
    ackMsgNo: Optional[str] = field(default=None)  # noqa: N815
    packet_type: Optional[str] = field(default=None)
    timestamp: float = field(default_factory=_init_timestamp, compare=False, hash=False)
    # Holds the raw text string to be sent over the wire
    # or holds the raw string from input packet
    raw: Optional[str] = field(default=None, compare=False, hash=False)
    raw_dict: dict = field(
        repr=False, default_factory=lambda: {}, compare=False, hash=False
    )
    # Built by calling prepare().  raw needs this built first.
    payload: Optional[str] = field(default=None)

    # Fields related to sending packets out
    send_count: int = field(repr=False, default=0, compare=False, hash=False)
    retry_count: int = field(repr=False, default=3, compare=False, hash=False)
    last_send_time: float = field(repr=False, default=0, compare=False, hash=False)
    # Was the packet acked?
    acked: bool = field(repr=False, default=False, compare=False, hash=False)
    # Was the packet previously processed (for dupe checking)
    processed: bool = field(repr=False, default=False, compare=False, hash=False)

    # Do we allow this packet to be saved to send later?
    allow_delay: bool = field(repr=False, default=True, compare=False, hash=False)
    path: List[str] = field(default_factory=list, compare=False, hash=False)
    via: Optional[str] = field(default=None, compare=False, hash=False)

    def get(self, key: str, default: Optional[str] = None):
        return getattr(self, key, default)

    @property
    def key(self) -> str:
        """Build a key for finding this packet in a dict."""
        return f"{self.from_call}:{self.addresse}:{self.msgNo}"

    def update_timestamp(self) -> None:
        self.timestamp = _init_timestamp()

    @property
    def human_info(self) -> str:
        """Build a human readable string for this packet.

        This doesn't include the from to and type, but just
        the human readable payload.
        """
        self.prepare()
        msg = self._filter_for_send(self.raw).rstrip("\n")
        return msg

    def prepare(self, create_msg_number=False) -> None:
        """Do stuff here that is needed prior to sending over the air."""
        # now build the raw message for sending
        if not self.msgNo and create_msg_number:
            self.msgNo = _init_msgNo()
        self._build_payload()
        self._build_raw()

    def _build_payload(self) -> None:
        """The payload is the non headers portion of the packet."""
        if not self.to_call:
            raise ValueError(
                "to_call isn't set. Must set to_call before calling prepare()"
            )

        # The base packet class has no real payload
        self.payload = f":{self.to_call.ljust(9)}"

    def _build_raw(self) -> None:
        """Build the self.raw which is what is sent over the air."""
        self.raw = "{}>APZ100:{}".format(
            self.from_call,
            self.payload,
        )

    def _filter_for_send(self, msg) -> str:
        """Filter and format message string for FCC."""
        # max?  ftm400 displays 64, raw msg shows 74
        # and ftm400-send is max 64.  setting this to
        # 67 displays 64 on the ftm400. (+3 {01 suffix)
        # feature req: break long ones into two msgs
        if not msg:
            return ""

        message = msg[:67]
        # We all miss George Carlin
        return re.sub(
            "fuck|shit|cunt|piss|cock|bitch",
            "****",
            message,
            flags=re.IGNORECASE,
        )

    def __str__(self) -> str:
        """Show the raw version of the packet"""
        self.prepare()
        if not self.raw:
            raise ValueError("self.raw is unset")
        return self.raw

    def __repr__(self) -> str:
        """Build the repr version of the packet."""
        return (
            f"{self.__class__.__name__}:"
            f" From: {self.from_call}  "
            f"   To: {self.to_call}"
        )


@dataclass_json
@dataclass(unsafe_hash=True)
class AckPacket(Packet):
    _type: str = field(default="AckPacket", hash=False)

    def _build_payload(self):
        self.payload = f":{self.to_call: <9}:ack{self.msgNo}"


@dataclass_json
@dataclass(unsafe_hash=True)
class BulletinPacket(Packet):
    _type: str = "BulletinPacket"
    # Holds the encapsulated packet
    bid: Optional[str] = field(default="1")
    message_text: Optional[str] = field(default=None)

    @property
    def key(self) -> str:
        """Build a key for finding this packet in a dict."""
        return f"{self.from_call}:BLN{self.bid}"

    @property
    def human_info(self) -> str:
        return f"BLN{self.bid} {self.message_text}"

    def _build_payload(self) -> None:
        self.payload = f":BLN{self.bid:<9}" f":{self.message_text}"


@dataclass_json
@dataclass(unsafe_hash=True)
class RejectPacket(Packet):
    _type: str = field(default="RejectPacket", hash=False)
    response: Optional[str] = field(default=None)

    def __post__init__(self):
        if self.response:
            LOG.warning("Response set!")

    def _build_payload(self):
        self.payload = f":{self.to_call: <9}:rej{self.msgNo}"


@dataclass_json
@dataclass(unsafe_hash=True)
class MessagePacket(Packet):
    _type: str = field(default="MessagePacket", hash=False)
    message_text: Optional[str] = field(default=None)

    @property
    def human_info(self) -> str:
        self.prepare()
        return self._filter_for_send(self.message_text).rstrip("\n")

    def _build_payload(self):
        if self.msgNo:
            self.payload = ":{}:{}{{{}".format(
                self.to_call.ljust(9),
                self._filter_for_send(self.message_text).rstrip("\n"),
                str(self.msgNo),
            )
        else:
            self.payload = ":{}:{}".format(
                self.to_call.ljust(9),
                self._filter_for_send(self.message_text).rstrip("\n"),
            )


@dataclass_json
@dataclass(unsafe_hash=True)
class StatusPacket(Packet):
    _type: str = field(default="StatusPacket", hash=False)
    status: Optional[str] = field(default=None)
    messagecapable: bool = field(default=False)
    comment: Optional[str] = field(default=None)
    raw_timestamp: Optional[str] = field(default=None)

    def _build_payload(self):
        self.payload = ":{}:{}{{{}".format(
            self.to_call.ljust(9),
            self._filter_for_send(self.status).rstrip("\n"),
            str(self.msgNo),
        )

    @property
    def human_info(self) -> str:
        self.prepare()
        return self.status


@dataclass_json
@dataclass(unsafe_hash=True)
class GPSPacket(Packet):
    _type: str = field(default="GPSPacket", hash=False)
    latitude: float = field(default=0.00)
    longitude: float = field(default=0.00)
    altitude: float = field(default=0.00)
    rng: float = field(default=0.00)
    posambiguity: int = field(default=0)
    messagecapable: bool = field(default=False)
    comment: Optional[str] = field(default=None)
    symbol: str = field(default="l")
    symbol_table: str = field(default="/")
    raw_timestamp: Optional[str] = field(default=None)
    object_name: Optional[str] = field(default=None)
    object_format: Optional[str] = field(default=None)
    alive: Optional[bool] = field(default=None)
    course: Optional[int] = field(default=None)
    speed: Optional[float] = field(default=None)
    phg: Optional[str] = field(default=None)
    phg_power: Optional[int] = field(default=None)
    phg_height: Optional[float] = field(default=None)
    phg_gain: Optional[int] = field(default=None)
    phg_dir: Optional[str] = field(default=None)
    phg_range: Optional[float] = field(default=None)
    phg_rate: Optional[int] = field(default=None)
    # http://www.aprs.org/datum.txt
    daodatumbyte: Optional[str] = field(default=None)

    def _build_time_zulu(self):
        """Build the timestamp in UTC/zulu."""
        if self.timestamp:
            return datetime.utcfromtimestamp(self.timestamp).strftime("%d%H%M")

    def _build_payload(self):
        """The payload is the non headers portion of the packet."""
        time_zulu = self._build_time_zulu()
        lat = aprslib_util.latitude_to_ddm(self.latitude)
        long = aprslib_util.longitude_to_ddm(self.longitude)
        payload = [
            "@" if self.timestamp else "!",
            time_zulu,
            lat,
            self.symbol_table,
            long,
            self.symbol,
        ]

        if self.comment:
            payload.append(self._filter_for_send(self.comment))

        self.payload = "".join(payload)

    def _build_raw(self):
        self.raw = f"{self.from_call}>{self.to_call},WIDE2-1:" f"{self.payload}"

    @property
    def human_info(self) -> str:
        h_str = []
        h_str.append(f"Lat:{self.latitude:03.3f}")
        h_str.append(f"Lon:{self.longitude:03.3f}")
        if self.altitude:
            h_str.append(f"Altitude {self.altitude:03.0f}")
        if self.speed:
            h_str.append(f"Speed {self.speed:03.0f}MPH")
        if self.course:
            h_str.append(f"Course {self.course:03.0f}")
        if self.rng:
            h_str.append(f"RNG {self.rng:03.0f}")
        if self.phg:
            h_str.append(f"PHG {self.phg}")

        return " ".join(h_str)


@dataclass_json
@dataclass(unsafe_hash=True)
class BeaconPacket(GPSPacket):
    _type: str = field(default="BeaconPacket", hash=False)

    def _build_payload(self):
        """The payload is the non headers portion of the packet."""
        time_zulu = self._build_time_zulu()
        lat = aprslib_util.latitude_to_ddm(self.latitude)
        lon = aprslib_util.longitude_to_ddm(self.longitude)

        self.payload = f"@{time_zulu}z{lat}{self.symbol_table}" f"{lon}"

        if self.comment:
            comment = self._filter_for_send(self.comment)
            self.payload = f"{self.payload}{self.symbol}{comment}"
        else:
            self.payload = f"{self.payload}{self.symbol}APRSD Beacon"

    def _build_raw(self):
        self.raw = f"{self.from_call}>APZ100:" f"{self.payload}"

    @property
    def key(self) -> str:
        """Build a key for finding this packet in a dict."""
        if self.raw_timestamp:
            return f"{self.from_call}:{self.raw_timestamp}"
        else:
            return f"{self.from_call}:{self.human_info.replace(' ', '')}"

    @property
    def human_info(self) -> str:
        h_str = []
        h_str.append(f"Lat:{self.latitude:03.3f}")
        h_str.append(f"Lon:{self.longitude:03.3f}")
        h_str.append(f"{self.comment}")
        return " ".join(h_str)


@dataclass_json
@dataclass(unsafe_hash=True)
class MicEPacket(GPSPacket):
    _type: str = field(default="MicEPacket", hash=False)
    messagecapable: bool = False
    mbits: Optional[str] = None
    mtype: Optional[str] = None
    telemetry: Optional[dict] = field(default=None)
    # in MPH
    speed: float = 0.00
    # 0 to 360
    course: int = 0

    @property
    def key(self) -> str:
        """Build a key for finding this packet in a dict."""
        return f"{self.from_call}:{self.human_info.replace(' ', '')}"

    @property
    def human_info(self) -> str:
        h_info = super().human_info
        return f"{h_info} {self.mbits} mbits"


@dataclass_json
@dataclass(unsafe_hash=True)
class TelemetryPacket(GPSPacket):
    _type: str = field(default="TelemetryPacket", hash=False)
    messagecapable: bool = False
    mbits: Optional[str] = None
    mtype: Optional[str] = None
    telemetry: Optional[dict] = field(default=None)
    tPARM: Optional[list[str]] = field(default=None)  # noqa: N815
    tUNIT: Optional[list[str]] = field(default=None)  # noqa: N815
    # in MPH
    speed: float = 0.00
    # 0 to 360
    course: int = 0

    @property
    def key(self) -> str:
        """Build a key for finding this packet in a dict."""
        if self.raw_timestamp:
            return f"{self.from_call}:{self.raw_timestamp}"
        else:
            return f"{self.from_call}:{self.human_info.replace(' ', '')}"

    @property
    def human_info(self) -> str:
        h_info = super().human_info
        return f"{h_info} {self.telemetry}"


@dataclass_json
@dataclass(unsafe_hash=True)
class ObjectPacket(GPSPacket):
    _type: str = field(default="ObjectPacket", hash=False)
    alive: bool = True
    raw_timestamp: Optional[str] = None
    symbol: str = field(default="r")
    # in MPH
    speed: float = 0.00
    # 0 to 360
    course: int = 0

    def _build_payload(self):
        time_zulu = self._build_time_zulu()
        lat = aprslib_util.latitude_to_ddm(self.latitude)
        long = aprslib_util.longitude_to_ddm(self.longitude)

        self.payload = f"*{time_zulu}z{lat}{self.symbol_table}" f"{long}{self.symbol}"

        if self.comment:
            comment = self._filter_for_send(self.comment)
            self.payload = f"{self.payload}{comment}"

    def _build_raw(self):
        """
        REPEAT builds packets like
        reply = "{}>APZ100:;{:9s}*{}z{}r{:.3f}MHz {} {}".format(
                fromcall, callsign, time_zulu, latlon, freq, uplink_tone, offset,
            )
        where fromcall is the callsign that is sending the packet
        callsign is the station callsign for the object
        The frequency, uplink_tone, offset is part of the comment
        """

        self.raw = f"{self.from_call}>APZ100:;{self.to_call:9s}" f"{self.payload}"

    @property
    def human_info(self) -> str:
        h_info = super().human_info
        return f"{h_info} {self.comment}"


@dataclass(unsafe_hash=True)
class WeatherPacket(GPSPacket, DataClassJsonMixin):
    _type: str = field(default="WeatherPacket", hash=False)
    symbol: str = "_"
    wind_speed: float = 0.00
    wind_direction: int = 0
    wind_gust: float = 0.00
    temperature: float = 0.00
    # in inches.  1.04 means 1.04 inches
    rain_1h: float = 0.00
    rain_24h: float = 0.00
    rain_since_midnight: float = 0.00
    humidity: int = 0
    pressure: float = 0.00
    comment: Optional[str] = field(default=None)
    luminosity: Optional[int] = field(default=None)
    wx_raw_timestamp: Optional[str] = field(default=None)
    course: Optional[int] = field(default=None)
    speed: Optional[float] = field(default=None)

    def _translate(self, raw: dict) -> dict:
        for key in raw["weather"]:
            raw[key] = raw["weather"][key]

        # If we have the broken aprslib, then we need to
        # Convert the course and speed to wind_speed and wind_direction
        # aprslib issue #80
        # https://github.com/rossengeorgiev/aprs-python/issues/80
        # Wind speed and course is option in the SPEC.
        # For some reason aprslib multiplies the speed by 1.852.
        if "wind_speed" not in raw and "wind_direction" not in raw:
            # Most likely this is the broken aprslib
            # So we need to convert the wind_gust speed
            raw["wind_gust"] = round(raw.get("wind_gust", 0) / 0.44704, 3)
        if "wind_speed" not in raw:
            wind_speed = raw.get("speed")
            if wind_speed:
                raw["wind_speed"] = round(wind_speed / 1.852, 3)
                raw["weather"]["wind_speed"] = raw["wind_speed"]
            if "speed" in raw:
                del raw["speed"]
            # Let's adjust the rain numbers as well, since it's wrong
            raw["rain_1h"] = round((raw.get("rain_1h", 0) / 0.254) * 0.01, 3)
            raw["weather"]["rain_1h"] = raw["rain_1h"]
            raw["rain_24h"] = round((raw.get("rain_24h", 0) / 0.254) * 0.01, 3)
            raw["weather"]["rain_24h"] = raw["rain_24h"]
            raw["rain_since_midnight"] = round(
                (raw.get("rain_since_midnight", 0) / 0.254) * 0.01, 3
            )
            raw["weather"]["rain_since_midnight"] = raw["rain_since_midnight"]

        if "wind_direction" not in raw:
            wind_direction = raw.get("course")
            if wind_direction:
                raw["wind_direction"] = wind_direction
                raw["weather"]["wind_direction"] = raw["wind_direction"]
            if "course" in raw:
                del raw["course"]

        del raw["weather"]
        return raw

    @classmethod
    def from_dict(cls: Type[A], kvs: Json, *, infer_missing=False) -> A:
        """Create from a dictionary that has come directly from aprslib parse"""
        raw = cls._translate(cls, kvs)  # type: ignore
        return super().from_dict(raw)

    @property
    def key(self) -> str:
        """Build a key for finding this packet in a dict."""
        if self.raw_timestamp:
            return f"{self.from_call}:{self.raw_timestamp}"
        elif self.wx_raw_timestamp:
            return f"{self.from_call}:{self.wx_raw_timestamp}"

    @property
    def human_info(self) -> str:
        h_str = []
        h_str.append(f"Temp {self.temperature:03.0f}F")
        h_str.append(f"Humidity {self.humidity}%")
        h_str.append(f"Wind {self.wind_speed:03.0f}MPH@{self.wind_direction}")
        h_str.append(f"Pressure {self.pressure}mb")
        h_str.append(f"Rain {self.rain_24h}in/24hr")

        return " ".join(h_str)

    def _build_payload(self):
        """Build an uncompressed weather packet

         Format =

        _CSE/SPDgXXXtXXXrXXXpXXXPXXXhXXbXXXXX%type NEW FORMAT APRS793 June 97
                                                   NOT BACKWARD COMPATIBLE


         Where: CSE/SPD is wind direction and sustained 1 minute speed
         t is in degrees F

         r is Rain per last 60 minutes
             1.04 inches of rain will show as r104
         p is precipitation per last 24 hours (sliding 24 hour window)
         P is precip per last 24 hours since midnight
         b is Baro in tenths of a mb
         h is humidity in percent. 00=100
         g is Gust (peak winds in last 5 minutes)
         # is the raw rain counter for remote WX stations
         See notes on remotes below
         % shows software type d=Dos, m=Mac, w=Win, etc
         type shows type of WX instrument

        """
        time_zulu = self._build_time_zulu()

        contents = [
            f"@{time_zulu}z{self.latitude}{self.symbol_table}",
            f"{self.longitude}{self.symbol}",
            f"{self.wind_direction:03d}",
            # Speed = sustained 1 minute wind speed in mph
            f"{self.symbol_table}",
            f"{self.wind_speed:03.0f}",
            # wind gust (peak wind speed in mph in the last 5 minutes)
            f"g{self.wind_gust:03.0f}",
            # Temperature in degrees F
            f"t{self.temperature:03.0f}",
            # Rainfall (in hundredths of an inch) in the last hour
            f"r{self.rain_1h * 100:03.0f}",
            # Rainfall (in hundredths of an inch) in last 24 hours
            f"p{self.rain_24h * 100:03.0f}",
            # Rainfall (in hundredths of an inch) since midnigt
            f"P{self.rain_since_midnight * 100:03.0f}",
            # Humidity
            f"h{self.humidity:02d}",
            # Barometric pressure (in tenths of millibars/tenths of hPascal)
            f"b{self.pressure:05.0f}",
        ]
        if self.comment:
            comment = self.filter_for_send(self.comment)
            contents.append(comment)
        self.payload = "".join(contents)

    def _build_raw(self):
        self.raw = f"{self.from_call}>{self.to_call},WIDE1-1,WIDE2-1:" f"{self.payload}"


@dataclass(unsafe_hash=True)
class ThirdPartyPacket(Packet, DataClassJsonMixin):
    _type: str = "ThirdPartyPacket"
    # Holds the encapsulated packet
    subpacket: Optional[type[Packet]] = field(default=None, compare=True, hash=False)

    def __repr__(self):
        """Build the repr version of the packet."""
        repr_str = (
            f"{self.__class__.__name__}:"
            f" From: {self.from_call}  "
            f" To: {self.to_call}  "
            f" Subpacket: {repr(self.subpacket)}"
        )

        return repr_str

    @classmethod
    def from_dict(cls: Type[A], kvs: Json, *, infer_missing=False) -> A:
        obj = super().from_dict(kvs)
        obj.subpacket = factory(obj.subpacket)  # type: ignore
        return obj

    @property
    def key(self) -> str:
        """Build a key for finding this packet in a dict."""
        return f"{self.from_call}:{self.subpacket.key}"

    @property
    def human_info(self) -> str:
        sub_info = self.subpacket.human_info
        return f"{self.from_call}->{self.to_call} {sub_info}"


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass(unsafe_hash=True)
class UnknownPacket:
    """Catchall Packet for things we don't know about.

    All of the unknown attributes are stored in the unknown_fields
    """

    unknown_fields: CatchAll
    _type: str = "UnknownPacket"
    from_call: Optional[str] = field(default=None)
    to_call: Optional[str] = field(default=None)
    msgNo: str = field(default_factory=_init_msgNo)  # noqa: N815
    format: Optional[str] = field(default=None)
    raw: Optional[str] = field(default=None)
    raw_dict: dict = field(
        repr=False, default_factory=lambda: {}, compare=False, hash=False
    )
    path: List[str] = field(default_factory=list, compare=False, hash=False)
    packet_type: Optional[str] = field(default=None)
    via: Optional[str] = field(default=None, compare=False, hash=False)
    # Was the packet previously processed (for dupe checking)
    processed: bool = field(repr=False, default=False, compare=False, hash=False)

    @property
    def key(self) -> str:
        """Build a key for finding this packet in a dict."""
        return f"{self.from_call}:{self.packet_type}:{self.to_call}"

    @property
    def human_info(self) -> str:
        return str(self.unknown_fields)


TYPE_LOOKUP: dict[str, type[Packet]] = {
    PACKET_TYPE_BULLETIN: BulletinPacket,
    PACKET_TYPE_WX: WeatherPacket,
    PACKET_TYPE_WEATHER: WeatherPacket,
    PACKET_TYPE_MESSAGE: MessagePacket,
    PACKET_TYPE_ACK: AckPacket,
    PACKET_TYPE_REJECT: RejectPacket,
    PACKET_TYPE_MICE: MicEPacket,
    PACKET_TYPE_OBJECT: ObjectPacket,
    PACKET_TYPE_STATUS: StatusPacket,
    PACKET_TYPE_BEACON: BeaconPacket,
    PACKET_TYPE_UNKNOWN: UnknownPacket,
    PACKET_TYPE_THIRDPARTY: ThirdPartyPacket,
    PACKET_TYPE_TELEMETRY: TelemetryPacket,
}


def get_packet_type(packet: dict) -> str:
    """Decode the packet type from the packet."""

    pkt_format = packet.get("format")
    msg_response = packet.get("response")
    packet_type = PACKET_TYPE_UNKNOWN
    if pkt_format == "message" and msg_response == "ack":
        packet_type = PACKET_TYPE_ACK
    elif pkt_format == "message" and msg_response == "rej":
        packet_type = PACKET_TYPE_REJECT
    elif pkt_format == "message":
        packet_type = PACKET_TYPE_MESSAGE
    elif pkt_format == "mic-e":
        packet_type = PACKET_TYPE_MICE
    elif pkt_format == "object":
        packet_type = PACKET_TYPE_OBJECT
    elif pkt_format == "status":
        packet_type = PACKET_TYPE_STATUS
    elif pkt_format == PACKET_TYPE_BULLETIN:
        packet_type = PACKET_TYPE_BULLETIN
    elif pkt_format == PACKET_TYPE_BEACON:
        packet_type = PACKET_TYPE_BEACON
    elif pkt_format == PACKET_TYPE_TELEMETRY:
        packet_type = PACKET_TYPE_TELEMETRY
    elif pkt_format == PACKET_TYPE_WX:
        packet_type = PACKET_TYPE_WEATHER
    elif pkt_format == PACKET_TYPE_UNCOMPRESSED:
        if packet.get("symbol") == "_":
            packet_type = PACKET_TYPE_WEATHER
    elif pkt_format == PACKET_TYPE_THIRDPARTY:
        packet_type = PACKET_TYPE_THIRDPARTY

    if packet_type == PACKET_TYPE_UNKNOWN:
        if "latitude" in packet:
            packet_type = PACKET_TYPE_BEACON
        else:
            packet_type = PACKET_TYPE_UNKNOWN
    return packet_type


def is_message_packet(packet: dict) -> bool:
    return get_packet_type(packet) == PACKET_TYPE_MESSAGE


def is_ack_packet(packet: dict) -> bool:
    return get_packet_type(packet) == PACKET_TYPE_ACK


def is_mice_packet(packet: dict[Any, Any]) -> bool:
    return get_packet_type(packet) == PACKET_TYPE_MICE


def factory(raw_packet: dict[Any, Any]) -> type[Packet]:
    """Factory method to create a packet from a raw packet string."""
    raw = raw_packet
    if "_type" in raw:
        cls = globals()[raw["_type"]]
        return cls.from_dict(raw)

    raw["raw_dict"] = raw.copy()
    raw = _translate_fields(raw)

    packet_type = get_packet_type(raw)

    raw["packet_type"] = packet_type
    packet_class = TYPE_LOOKUP[packet_type]
    if packet_type == PACKET_TYPE_WX:
        # the weather information is in a dict
        # this brings those values out to the outer dict
        packet_class = WeatherPacket
    elif packet_type == PACKET_TYPE_OBJECT and "weather" in raw:
        packet_class = WeatherPacket
    elif packet_type == PACKET_TYPE_UNKNOWN:
        # Try and figure it out here
        if "latitude" in raw:
            packet_class = GPSPacket
        else:
            # LOG.warning(raw)
            packet_class = UnknownPacket

    raw.get("addresse", raw.get("to_call"))

    # TODO: Find a global way to enable/disable this
    # LOGU.opt(colors=True).info(
    #     f"factory(<green>{packet_type: <8}</green>):"
    #     f"(<red>{packet_class.__name__: <13}</red>): "
    #     f"<light-blue>{raw.get('from_call'): <9}</light-blue> -> <cyan>{to: <9}</cyan>")
    # LOG.info(raw.get('msgNo'))

    return packet_class().from_dict(raw)  # type: ignore
