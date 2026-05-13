import datetime
import logging
import threading

from oslo_config import cfg

from aprsd.packets import core
from aprsd.utils import objectstore

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


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
            cls._instance.lock = threading.RLock()
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
                'total_tracked': self.total_tracked,
            }
            pkts = {}
            for key in self.data:
                last_send_time = self.data[key].last_send_time
                if serializable and isinstance(last_send_time, datetime.datetime):
                    last_send_time = last_send_time.isoformat()
                pkts[key] = {
                    'last_send_time': last_send_time,
                    'send_count': self.data[key].send_count,
                    'retry_count': self.data[key].retry_count,
                    'message': self.data[key].raw,
                }
            stats['packets'] = pkts
        return stats

    def rx(self, packet: type[core.Packet]) -> None:
        """When we get a packet from the network, check if we should remove it."""
        if isinstance(packet, core.AckPacket):
            self._remove(packet.msgNo)
        elif isinstance(packet, core.RejectPacket):
            self._remove(packet.msgNo)
        elif hasattr(packet, 'ackMsgNo'):
            # Got a piggyback ack, so remove the original message
            self._remove(packet.ackMsgNo)

    def tx(self, packet: type[core.Packet]) -> None:
        """Add a packet that was sent.

        BeaconPackets are skipped — they are fire-and-forget and never
        receive an ack, so tracking them only causes the scheduler to
        re-transmit them as unwanted duplicates.

        AckPackets that are already being tracked are NOT reset — this
        prevents digipeated duplicates of the same message from restarting
        the ack retry counter, which caused ack floods on RF.
        """
        if isinstance(packet, core.BeaconPacket):
            return
        with self.lock:
            key = packet.msgNo
            if key in self.data and isinstance(packet, core.AckPacket):
                # Already tracking this ack — don't reset send_count.
                # This happens when the same message arrives via multiple
                # digipeater paths and each copy triggers an ack send.
                return
            packet.send_count = 0
            self.data[key] = packet
            self.total_tracked += 1

    def remove(self, key):
        self._remove(key)

    def load(self):
        """Load tracked packets from disk, filtering out stale BeaconPackets.

        BeaconPackets should never be retried (they are fire-and-forget),
        but older versions persisted them to disk.  Strip them on load so
        they don't get retransmitted after a restart.
        """
        super().load()
        with self.lock:
            stale = [
                key
                for key, pkt in self.data.items()
                if isinstance(pkt, core.BeaconPacket)
                or (isinstance(pkt, dict) and pkt.get('_type') == 'BeaconPacket')
            ]
            for key in stale:
                del self.data[key]
            if stale:
                LOG.info(
                    f'PacketTrack: removed {len(stale)} stale BeaconPacket(s) '
                    f'from persisted data.',
                )

    def _remove(self, key):
        with self.lock:
            try:
                del self.data[key]
            except KeyError:
                pass
