import logging
import threading
import time

LOG = logging.getLogger("APRSD")

PACKET_TYPE_MESSAGE = "message"
PACKET_TYPE_ACK = "ack"
PACKET_TYPE_MICE = "mic-e"


class PacketList:
    """Class to track all of the packets rx'd and tx'd by aprsd."""

    _instance = None

    packet_list = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.packet_list = {}
            cls._instance.lock = threading.Lock()
        return cls._instance

    def __iter__(self):
        with self.lock:
            return iter(self.packet_list)

    def add(self, packet):
        with self.lock:
            now = time.time()
            ts = str(now).split(".")[0]
            self.packet_list[ts] = packet


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
