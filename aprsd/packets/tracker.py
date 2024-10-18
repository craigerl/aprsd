import datetime
import logging

from oslo_config import cfg

from aprsd.packets import core
from aprsd.utils import objectstore


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class PacketTrack(objectstore.ObjectStoreMixin):
    """Class to keep track of outstanding text messages.

    This is a thread safe class that keeps track of active
    messages.

    When a message is asked to be sent, it is placed into this
    class via it's id.  The TextMessage class's send() method
    automatically adds itself to this class.  When the ack is
    recieved from the radio, the message object is removed from
    this class.
    """

    _instance = None
    _start_time = None

    data: dict = {}
    total_tracked: int = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._start_time = datetime.datetime.now()
            cls._instance._init_store()
        return cls._instance

    def __getitem__(self, name):
        with self.lock:
            return self.data[name]

    def __iter__(self):
        with self.lock:
            return iter(self.data)

    def keys(self):
        with self.lock:
            return self.data.keys()

    def items(self):
        with self.lock:
            return self.data.items()

    def values(self):
        with self.lock:
            return self.data.values()

    def stats(self, serializable=False):
        with self.lock:
            stats = {
                "total_tracked": self.total_tracked,
            }
            pkts = {}
            for key in self.data:
                last_send_time = self.data[key].last_send_time
                pkts[key] = {
                    "last_send_time": last_send_time,
                    "send_count": self.data[key].send_count,
                    "retry_count": self.data[key].retry_count,
                    "message": self.data[key].raw,
                }
            stats["packets"] = pkts
        return stats

    def rx(self, packet: type[core.Packet]) -> None:
        """When we get a packet from the network, check if we should remove it."""
        if isinstance(packet, core.AckPacket):
            self._remove(packet.msgNo)
        elif isinstance(packet, core.RejectPacket):
            self._remove(packet.msgNo)
        elif hasattr(packet, "ackMsgNo"):
            # Got a piggyback ack, so remove the original message
            self._remove(packet.ackMsgNo)

    def tx(self, packet: type[core.Packet]) -> None:
        """Add a packet that was sent."""
        with self.lock:
            key = packet.msgNo
            packet.send_count = 0
            self.data[key] = packet
            self.total_tracked += 1

    def remove(self, key):
        self._remove(key)

    def _remove(self, key):
        with self.lock:
            try:
                del self.data[key]
            except KeyError:
                pass
