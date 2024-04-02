import datetime
import threading

from oslo_config import cfg
import wrapt

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
    def stats(self, serializable=False):
        stats = {
            "total_tracked": self.total_tracked,
        }
        pkts = {}
        for key in self.data:
            last_send_time = self.data[key].last_send_time
            last_send_attempt = self.data[key]._last_send_attempt
            pkts[key] = {
                "last_send_time": last_send_time,
                "last_send_attempt": last_send_attempt,
                "retry_count": self.data[key].retry_count,
                "message": self.data[key].raw,
            }
        stats["packets"] = pkts
        return stats

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
