import abc
from dataclasses import asdict, dataclass, field
from datetime import datetime
import logging
import re
import time
# Due to a failure in python 3.8
from typing import List

import dacite
from dataclasses_json import dataclass_json

from aprsd.utils import counter


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
PACKET_TYPE_THIRDPARTY = "thirdparty"
PACKET_TYPE_UNCOMPRESSED = "uncompressed"

NO_DATE = datetime(1900, 10, 24)


def _init_timestamp():
    """Build a unix style timestamp integer"""
    return int(round(time.time()))


def _init_send_time():
    # We have to use a datetime here, or the json encoder
    # Fails on a NoneType.
    return NO_DATE


def _init_msgNo():    # noqa: N802
    """For some reason __post__init doesn't get called.

    So in order to initialize the msgNo field in the packet
    we use this workaround.
    """
    c = counter.PacketCounter()
    c.increment()
    return c.value


def factory_from_dict(packet_dict):
    pkt_type = get_packet_type(packet_dict)
    if pkt_type:
        cls = TYPE_LOOKUP[pkt_type]
        return cls.from_dict(packet_dict)


def factory_from_json(packet_dict):
    pkt_type = get_packet_type(packet_dict)
    if pkt_type:
        return TYPE_LOOKUP[pkt_type].from_json(packet_dict)


@dataclass_json
@dataclass(unsafe_hash=True)
class Packet(metaclass=abc.ABCMeta):
    from_call: str = field(default=None)
    to_call: str = field(default=None)
    addresse: str = field(default=None)
    format: str = field(default=None)
    msgNo: str = field(default_factory=_init_msgNo)   # noqa: N815
    packet_type: str = field(default=None)
    timestamp: float = field(default_factory=_init_timestamp, compare=False, hash=False)
    # Holds the raw text string to be sent over the wire
    # or holds the raw string from input packet
    raw: str = field(default=None, compare=False, hash=False)
    raw_dict: dict = field(repr=False, default_factory=lambda: {}, compare=False, hash=False)
    # Built by calling prepare().  raw needs this built first.
    payload: str = field(default=None)

    # Fields related to sending packets out
    send_count: int = field(repr=False, default=0, compare=False, hash=False)
    retry_count: int = field(repr=False, default=3, compare=False, hash=False)
    # last_send_time: datetime = field(
    #    metadata=dc_json_config(
    #        encoder=datetime.isoformat,
    #        decoder=datetime.fromisoformat,
    #    ),
    #    repr=True,
    #    default_factory=_init_send_time,
    #    compare=False,
    #    hash=False
    # )
    last_send_time: float = field(repr=False, default=0, compare=False, hash=False)
    last_send_attempt: int = field(repr=False, default=0, compare=False, hash=False)

    # Do we allow this packet to be saved to send later?
    allow_delay: bool = field(repr=False, default=True, compare=False, hash=False)
    path: List[str] = field(default_factory=list, compare=False, hash=False)
    via: str = field(default=None, compare=False, hash=False)

    def __post__init__(self):
        LOG.warning(f"POST INIT {self}")

    @property
    def json(self):
        """
        get the json formated string
        """
        return self.to_json()

    def get(self, key, default=None):
        """Emulate a getter on a dict."""
        if hasattr(self, key):
            return getattr(self, key)
        else:
            return default

    @property
    def key(self):
        """Build a key for finding this packet in a dict."""
        return f"{self.from_call}:{self.addresse}:{self.msgNo}"

    def update_timestamp(self):
        self.timestamp = _init_timestamp()

    def prepare(self):
        """Do stuff here that is needed prior to sending over the air."""
        # now build the raw message for sending
        self._build_payload()
        self._build_raw()

    def _build_payload(self):
        """The payload is the non headers portion of the packet."""
        msg = self._filter_for_send().rstrip("\n")
        self.payload = (
            f":{self.to_call.ljust(9)}"
            f":{msg}"
        )

    def _build_raw(self):
        """Build the self.raw which is what is sent over the air."""
        self.raw = "{}>APZ100:{}".format(
            self.from_call,
            self.payload,
        )

    @staticmethod
    def factory(raw_packet):
        """Factory method to create a packet from a raw packet string."""
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
        if packet_type == PACKET_TYPE_THIRDPARTY:
            # We have an encapsulated packet!
            # So we need to decode it and return the inner packet
            # as the packet we are going to process.
            # This is a recursive call to the factory
            subpacket_raw = raw["subpacket"]
            subpacket = Packet.factory(subpacket_raw)
            del raw["subpacket"]
            # raw["subpacket"] = subpacket
            packet = dacite.from_dict(data_class=class_name, data=raw)
            packet.subpacket = subpacket
            return packet

        if packet_type == PACKET_TYPE_UNKNOWN:
            # Try and figure it out here
            if "latitude" in raw:
                class_name = GPSPacket

        if packet_type == PACKET_TYPE_WX:
            # the weather information is in a dict
            # this brings those values out to the outer dict

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
                raw["rain_1h"] = round((raw.get("rain_1h", 0) / .254) * .01, 3)
                raw["weather"]["rain_1h"] = raw["rain_1h"]
                raw["rain_24h"] = round((raw.get("rain_24h", 0) / .254) * .01, 3)
                raw["weather"]["rain_24h"] = raw["rain_24h"]
                raw["rain_since_midnight"] = round((raw.get("rain_since_midnight", 0) / .254) * .01, 3)
                raw["weather"]["rain_since_midnight"] = raw["rain_since_midnight"]

            if "wind_direction" not in raw:
                wind_direction = raw.get("course")
                if wind_direction:
                    raw["wind_direction"] = wind_direction
                    raw["weather"]["wind_direction"] = raw["wind_direction"]
                if "course" in raw:
                    del raw["course"]

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


@dataclass(unsafe_hash=True)
class AckPacket(Packet):
    response: str = field(default=None)

    def __post__init__(self):
        if self.response:
            LOG.warning("Response set!")

    def _build_payload(self):
        self.payload = f":{self.to_call.ljust(9)}:ack{self.msgNo}"


@dataclass(unsafe_hash=True)
class RejectPacket(Packet):
    response: str = field(default=None)

    def __post__init__(self):
        if self.response:
            LOG.warning("Response set!")

    def _build_payload(self):
        self.payload = f":{self.to_call.ljust(9)} :rej{self.msgNo}"


@dataclass_json
@dataclass(unsafe_hash=True)
class MessagePacket(Packet):
    message_text: str = field(default=None)

    def _filter_for_send(self) -> str:
        """Filter and format message string for FCC."""
        # max?  ftm400 displays 64, raw msg shows 74
        # and ftm400-send is max 64.  setting this to
        # 67 displays 64 on the ftm400. (+3 {01 suffix)
        # feature req: break long ones into two msgs
        message = self.message_text[:67]
        # We all miss George Carlin
        return re.sub("fuck|shit|cunt|piss|cock|bitch", "****", message)

    def _build_payload(self):
        self.payload = ":{}:{}{{{}".format(
            self.to_call.ljust(9),
            self._filter_for_send().rstrip("\n"),
            str(self.msgNo),
        )


@dataclass(unsafe_hash=True)
class StatusPacket(Packet):
    status: str = field(default=None)
    messagecapable: bool = field(default=False)
    comment: str = field(default=None)

    def _build_payload(self):
        raise NotImplementedError


@dataclass(unsafe_hash=True)
class GPSPacket(Packet):
    latitude: float = field(default=0.00)
    longitude: float = field(default=0.00)
    altitude: float = field(default=0.00)
    rng: float = field(default=0.00)
    posambiguity: int = field(default=0)
    comment: str = field(default=None)
    symbol: str = field(default="l")
    symbol_table: str = field(default="/")

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
            local_dt = datetime.fromtimestamp(self.timestamp)
        else:
            local_dt = datetime.now()
            self.timestamp = datetime.timestamp(local_dt)

        utc_offset_timedelta = datetime.utcnow() - local_dt
        result_utc_datetime = local_dt + utc_offset_timedelta
        time_zulu = result_utc_datetime.strftime("%d%H%M")
        return time_zulu

    def _build_payload(self):
        """The payload is the non headers portion of the packet."""
        time_zulu = self._build_time_zulu()
        lat = self.latitude
        long = self.longitude
        self.payload = (
            f"@{time_zulu}z{lat}{self.symbol_table}"
            f"{long}{self.symbol}"
        )

        if self.comment:
            self.payload = f"{self.payload}{self.comment}"

    def _build_raw(self):
        self.raw = (
            f"{self.from_call}>{self.to_call},WIDE2-1:"
            f"{self.payload}"
        )


@dataclass(unsafe_hash=True)
class BeaconPacket(GPSPacket):
    def _build_payload(self):
        """The payload is the non headers portion of the packet."""
        time_zulu = self._build_time_zulu()
        lat = self.convert_latitude(self.latitude)
        long = self.convert_longitude(self.longitude)

        self.payload = (
            f"@{time_zulu}z{lat}{self.symbol_table}"
            f"{long}{self.symbol}APRSD Beacon"
        )

    def _build_raw(self):
        self.raw = (
            f"{self.from_call}>APZ100:"
            f"{self.payload}"
        )


@dataclass
class MicEPacket(GPSPacket):
    messagecapable: bool = False
    mbits: str = None
    mtype: str = None
    # in MPH
    speed: float = 0.00
    # 0 to 360
    course: int = 0

    def _build_payload(self):
        raise NotImplementedError


@dataclass
class ObjectPacket(GPSPacket):
    alive: bool = True
    raw_timestamp: str = None
    symbol: str = field(default="r")
    # in MPH
    speed: float = 0.00
    # 0 to 360
    course: int = 0

    def _build_payload(self):
        time_zulu = self._build_time_zulu()
        lat = self.convert_latitude(self.latitude)
        long = self.convert_longitude(self.longitude)

        self.payload = (
            f"*{time_zulu}z{lat}{self.symbol_table}"
            f"{long}{self.symbol}"
        )

        if self.comment:
            self.payload = f"{self.payload}{self.comment}"

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

        self.raw = (
            f"{self.from_call}>APZ100:;{self.to_call:9s}"
            f"{self.payload}"
        )


@dataclass()
class WeatherPacket(GPSPacket):
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
    comment: str = None

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
            f"{self.symbol_table}", f"{self.wind_speed:03.0f}",
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
        self.payload = "".join(contents)

    def _build_raw(self):

        self.raw = (
            f"{self.from_call}>{self.to_call},WIDE1-1,WIDE2-1:"
            f"{self.payload}"
        )


class ThirdParty(Packet):
    # Holds the encapsulated packet
    subpacket: Packet = field(default=None, compare=True, hash=False)

    def __repr__(self):
        """Build the repr version of the packet."""
        repr_str = (
            f"{self.__class__.__name__}:"
            f" From: {self.from_call}  "
            f" To: {self.to_call}  "
            f" Subpacket: {repr(self.subpacket)}"
        )

        return repr_str


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
    PACKET_TYPE_THIRDPARTY: ThirdParty,
}


def get_packet_type(packet: dict):
    """Decode the packet type from the packet."""

    pkt_format = packet.get("format", None)
    msg_response = packet.get("response", None)
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
    elif pkt_format == PACKET_TYPE_BEACON:
        packet_type = PACKET_TYPE_BEACON
    elif pkt_format == PACKET_TYPE_UNCOMPRESSED:
        if packet.get("symbol", None) == "_":
            packet_type = PACKET_TYPE_WX
    elif pkt_format == PACKET_TYPE_THIRDPARTY:
        packet_type = PACKET_TYPE_THIRDPARTY

    if packet_type == PACKET_TYPE_UNKNOWN:
        if "latitude" in packet:
            packet_type = PACKET_TYPE_BEACON
    return packet_type


def is_message_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_MESSAGE


def is_ack_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_ACK


def is_mice_packet(packet):
    return get_packet_type(packet) == PACKET_TYPE_MICE
