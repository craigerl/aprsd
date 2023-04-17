import abc
from dataclasses import asdict, dataclass, field
import datetime
import json
import logging
import re
import time
# Due to a failure in python 3.8
from typing import List

import dacite

from aprsd.utils import counter
from aprsd.utils import json as aprsd_json


LOG = logging.getLogger("APRSD")

PACKET_TYPE_MESSAGE = "message"
PACKET_TYPE_ACK = "ack"
PACKET_TYPE_REJECT = "reject"
PACKET_TYPE_MICE = "mic-e"
PACKET_TYPE_WX = "weather"
PACKET_TYPE_OBJECT = "object"
PACKET_TYPE_UNKNOWN = "unknown"
PACKET_TYPE_STATUS = "status"
PACKET_TYPE_BEACON = "beacon"
PACKET_TYPE_UNCOMPRESSED = "uncompressed"


def _int_timestamp():
    """Build a unix style timestamp integer"""
    return int(round(time.time()))


def _init_msgNo():    # noqa: N802
    """For some reason __post__init doesn't get called.

    So in order to initialize the msgNo field in the packet
    we use this workaround.
    """
    c = counter.PacketCounter()
    c.increment()
    return c.value


@dataclass
class Packet(metaclass=abc.ABCMeta):
    from_call: str
    to_call: str
    addresse: str = None
    format: str = None
    msgNo: str = field(default_factory=_init_msgNo)   # noqa: N815
    packet_type: str = None
    timestamp: float = field(default_factory=_int_timestamp)
    # Holds the raw text string to be sent over the wire
    # or holds the raw string from input packet
    raw: str = None
    raw_dict: dict = field(repr=False, default_factory=lambda: {})

    # Fields related to sending packets out
    send_count: int = field(repr=False, default=0)
    retry_count: int = field(repr=False, default=3)
    last_send_time: datetime.timedelta = field(repr=False, default=None)
    # Do we allow this packet to be saved to send later?
    allow_delay: bool = field(repr=False, default=True)

    def __post__init__(self):
        LOG.warning(f"POST INIT {self}")

    @property
    def __dict__(self):
        return asdict(self)

    @property
    def json(self):
        """
        get the json formated string
        """
        return json.dumps(self.__dict__, cls=aprsd_json.EnhancedJSONEncoder)

    def get(self, key, default=None):
        """Emulate a getter on a dict."""
        if hasattr(self, key):
            return getattr(self, key)
        else:
            return default

    def update_timestamp(self):
        self.timestamp = _int_timestamp()

    def prepare(self):
        """Do stuff here that is needed prior to sending over the air."""
        # now build the raw message for sending
        self._build_raw()

    def _build_raw(self):
        """Build the self.raw string which is what is sent over the air."""
        self.raw = self._filter_for_send().rstrip("\n")

    @staticmethod
    def factory(raw_packet):
        raw = raw_packet
        raw["raw_dict"] = raw.copy()
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
        name = self.__class__.__name__
        if header:
            if "tx" in header.lower():
                log_list.append(
                    f"{header}________({name}  "
                    f"TX:{self.send_count+1} of {self.retry_count})",
                )
            else:
                log_list.append(f"{header}________({name})")
        # log_list.append(f"  Packet  : {self.__class__.__name__}")
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
        log_list.append(f"{header}________({name})")

        LOG.info("\n".join(log_list))
        LOG.debug(repr(self))

    def _filter_for_send(self) -> str:
        """Filter and format message string for FCC."""
        # max?  ftm400 displays 64, raw msg shows 74
        # and ftm400-send is max 64.  setting this to
        # 67 displays 64 on the ftm400. (+3 {01 suffix)
        # feature req: break long ones into two msgs
        message = self.raw[:67]
        # We all miss George Carlin
        return re.sub("fuck|shit|cunt|piss|cock|bitch", "****", message)

    def __str__(self):
        """Show the raw version of the packet"""
        self.prepare()
        return self.raw

    def __repr__(self):
        """Build the repr version of the packet."""
        repr = (
            f"{self.__class__.__name__}:"
            f" From: {self.from_call}  "
            " To: "
        )

        return repr


@dataclass
class PathPacket(Packet):
    path: List[str] = field(default_factory=list)
    via: str = None

    def _build_raw(self):
        raise NotImplementedError


@dataclass
class AckPacket(PathPacket):
    response: str = None

    def __post__init__(self):
        if self.response:
            LOG.warning("Response set!")

    def _build_raw(self):
        """Build the self.raw which is what is sent over the air."""
        self.raw = "{}>APZ100::{}:ack{}".format(
            self.from_call,
            self.to_call.ljust(9),
            self.msgNo,
        )


@dataclass
class RejectPacket(PathPacket):
    response: str = None

    def __post__init__(self):
        if self.response:
            LOG.warning("Response set!")

    def _build_raw(self):
        """Build the self.raw which is what is sent over the air."""
        self.raw = "{}>APZ100::{} :rej{}".format(
            self.from_call,
            self.to_call.ljust(9),
            self.msgNo,
        )


@dataclass
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


@dataclass
class StatusPacket(PathPacket):
    status: str = None
    messagecapable: bool = False
    comment: str = None

    def _build_raw(self):
        raise NotImplementedError


@dataclass
class GPSPacket(PathPacket):
    latitude: float = 0.00
    longitude: float = 0.00
    altitude: float = 0.00
    rng: float = 0.00
    posambiguity: int = 0
    comment: str = None
    symbol: str = field(default="l")
    symbol_table: str = field(default="/")
    # in MPH
    speed: float = 0.00
    # 0 to 360
    course: int = 0

    def decdeg2dms(self, degrees_decimal):
        is_positive = degrees_decimal >= 0
        degrees_decimal = abs(degrees_decimal)
        minutes, seconds = divmod(degrees_decimal * 3600, 60)
        degrees, minutes = divmod(minutes, 60)
        degrees = degrees if is_positive else -degrees

        degrees = str(int(degrees)).replace("-", "0")
        minutes = str(int(minutes)).replace("-", "0")
        seconds = str(int(round(seconds * 0.01, 2) * 100))

        return {"degrees": degrees, "minutes": minutes, "seconds": seconds}

    def decdeg2dmm_m(self, degrees_decimal):
        is_positive = degrees_decimal >= 0
        degrees_decimal = abs(degrees_decimal)
        minutes, seconds = divmod(degrees_decimal * 3600, 60)
        degrees, minutes = divmod(minutes, 60)
        degrees = degrees if is_positive else -degrees

        degrees = abs(int(degrees))
        minutes = int(round(minutes + (seconds / 60), 2))
        hundredths = round(seconds / 60, 2)

        return {
            "degrees": degrees, "minutes": minutes, "seconds": seconds,
            "hundredths": hundredths,
        }

    def convert_latitude(self, degrees_decimal):
        det = self.decdeg2dmm_m(degrees_decimal)
        if degrees_decimal > 0:
            direction = "N"
        else:
            direction = "S"

        degrees = str(det.get("degrees")).zfill(2)
        minutes = str(det.get("minutes")).zfill(2)
        seconds = det.get("seconds")
        hun = det.get("hundredths")
        hundredths = f"{hun:.2f}".split(".")[1]

        LOG.debug(
            f"LAT degress {degrees}  minutes {str(minutes)} "
            f"seconds {seconds} hundredths {hundredths} direction {direction}",
        )

        lat = f"{degrees}{str(minutes)}.{hundredths}{direction}"
        return lat

    def convert_longitude(self, degrees_decimal):
        det = self.decdeg2dmm_m(degrees_decimal)
        if degrees_decimal > 0:
            direction = "E"
        else:
            direction = "W"

        degrees = str(det.get("degrees")).zfill(3)
        minutes = str(det.get("minutes")).zfill(2)
        seconds = det.get("seconds")
        hun = det.get("hundredths")
        hundredths = f"{hun:.2f}".split(".")[1]

        LOG.debug(
            f"LON degress {degrees}  minutes {str(minutes)} "
            f"seconds {seconds} hundredths {hundredths} direction {direction}",
        )

        lon = f"{degrees}{str(minutes)}.{hundredths}{direction}"
        return lon

    def _build_time_zulu(self):
        """Build the timestamp in UTC/zulu."""
        if self.timestamp:
            local_dt = datetime.datetime.fromtimestamp(self.timestamp)
        else:
            local_dt = datetime.datetime.now()
            self.timestamp = datetime.datetime.timestamp(local_dt)

        utc_offset_timedelta = datetime.datetime.utcnow() - local_dt
        result_utc_datetime = local_dt + utc_offset_timedelta
        time_zulu = result_utc_datetime.strftime("%d%H%M")
        return time_zulu

    def _build_raw(self):
        time_zulu = self._build_time_zulu()

        self.raw = (
            f"{self.from_call}>{self.to_call},WIDE2-1:"
            f"@{time_zulu}z{self.latitude}{self.symbol_table}"
            f"{self.longitude}{self.symbol}"
        )
        if self.comment:
            self.raw = f"{self.raw}{self.comment}"


@dataclass
class MicEPacket(GPSPacket):
    messagecapable: bool = False
    mbits: str = None
    mtype: str = None

    def _build_raw(self):
        raise NotImplementedError


@dataclass
class ObjectPacket(GPSPacket):
    alive: bool = True
    raw_timestamp: str = None
    symbol: str = field(default="r")

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
        time_zulu = self._build_time_zulu()
        lat = self.convert_latitude(self.latitude)
        long = self.convert_longitude(self.longitude)

        self.raw = (
            f"{self.from_call}>APZ100:;{self.to_call:9s}"
            f"*{time_zulu}z{lat}{self.symbol_table}"
            f"{long}{self.symbol}"
        )
        if self.comment:
            self.raw = f"{self.raw}{self.comment}"


@dataclass()
class WeatherPacket(GPSPacket):
    symbol: str = "_"
    wind_gust: float = 0.00
    temperature: float = 0.00
    # in inches.  1.04 means 1.04 inches
    rain_1h: float = 0.00
    rain_24h: float = 0.00
    rain_since_midnight: float = 0.00
    humidity: int = 0
    pressure: float = 0.00
    comment: str = None

    def _build_raw(self):
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

        course = "%03u" % self.course

        contents = [
            f"{self.from_call}>{self.to_call},WIDE1-1,WIDE2-1:",
            f"@{time_zulu}z{self.latitude}{self.symbol_table}",
            f"{self.longitude}{self.symbol}",
            # Add CSE = Course
            f"{course}",
            # Speed = sustained 1 minute wind speed in mph
            f"{self.symbol_table}", f"{self.speed:03.0f}",
            # wind gust (peak wind speed in mph in the last 5 minutes)
            f"g{self.wind_gust:03.0f}",
            # Temperature in degrees F
            f"t{self.temperature:03.0f}",
            # Rainfall (in hundredths of an inch) in the last hour
            f"r{self.rain_1h*100:03.0f}",
            # Rainfall (in hundredths of an inch) in last 24 hours
            f"p{self.rain_24h*100:03.0f}",
            # Rainfall (in hundredths of an inch) since midnigt
            f"P{self.rain_since_midnight*100:03.0f}",
            # Humidity
            f"h{self.humidity:02d}",
            # Barometric pressure (in tenths of millibars/tenths of hPascal)
            f"b{self.pressure:05.0f}",
        ]

        if self.comment:
            contents.append(self.comment)

        self.raw = "".join(contents)


TYPE_LOOKUP = {
    PACKET_TYPE_WX: WeatherPacket,
    PACKET_TYPE_MESSAGE: MessagePacket,
    PACKET_TYPE_ACK: AckPacket,
    PACKET_TYPE_REJECT: RejectPacket,
    PACKET_TYPE_MICE: MicEPacket,
    PACKET_TYPE_OBJECT: ObjectPacket,
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
