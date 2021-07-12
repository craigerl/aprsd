import logging
import threading
import time

LOG = logging.getLogger("APRSD")


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
