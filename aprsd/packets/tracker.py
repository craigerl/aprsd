import datetime
import threading

from oslo_config import cfg
import wrapt

from aprsd.threads import tx
from aprsd.utils import objectstore


CONF = cfg.CONF


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
    lock = threading.Lock()

    data: dict = {}
    total_tracked: int = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._start_time = datetime.datetime.now()
            cls._instance._init_store()
        return cls._instance

    @wrapt.synchronized(lock)
    def __getitem__(self, name):
        return self.data[name]

    @wrapt.synchronized(lock)
    def __iter__(self):
        return iter(self.data)

    @wrapt.synchronized(lock)
    def keys(self):
        return self.data.keys()

    @wrapt.synchronized(lock)
    def items(self):
        return self.data.items()

    @wrapt.synchronized(lock)
    def values(self):
        return self.data.values()

    @wrapt.synchronized(lock)
    def __len__(self):
        return len(self.data)

    @wrapt.synchronized(lock)
    def add(self, packet):
        key = packet.msgNo
        packet._last_send_attempt = 0
        self.data[key] = packet
        self.total_tracked += 1

    @wrapt.synchronized(lock)
    def get(self, key):
        return self.data.get(key, None)

    @wrapt.synchronized(lock)
    def remove(self, key):
        try:
            del self.data[key]
        except KeyError:
            pass

    def restart(self):
        """Walk the list of messages and restart them if any."""
        for key in self.data.keys():
            pkt = self.data[key]
            if pkt._last_send_attempt < pkt.retry_count:
                tx.send(pkt)

    def _resend(self, packet):
        packet._last_send_attempt = 0
        tx.send(packet)

    def restart_delayed(self, count=None, most_recent=True):
        """Walk the list of delayed messages and restart them if any."""
        if not count:
            # Send all the delayed messages
            for key in self.data.keys():
                pkt = self.data[key]
                if pkt._last_send_attempt == pkt._retry_count:
                    self._resend(pkt)
        else:
            # They want to resend <count> delayed messages
            tmp = sorted(
                self.data.items(),
                reverse=most_recent,
                key=lambda x: x[1].last_send_time,
            )
            pkt_list = tmp[:count]
            for (_key, pkt) in pkt_list:
                self._resend(pkt)
