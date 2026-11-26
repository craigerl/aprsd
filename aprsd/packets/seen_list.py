import datetime
import logging
import threading
from collections import OrderedDict

from oslo_config import cfg

from aprsd.packets import core
from aprsd.utils import objectstore

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class SeenList(objectstore.ObjectStoreMixin):
    """Global callsign seen list."""

    _instance = None
    data: OrderedDict = OrderedDict()
    maxlen: int = 1000

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.lock = threading.RLock()
            cls._instance.data = OrderedDict()
            cls._instance.maxlen = CONF.seen_list_maxlen
        return cls._instance

    def _restore_ordereddict(self):
        """Restore OrderedDict after loading from JSON (dict keeps order, but
        only OrderedDict has move_to_end / popitem(last=False)), then trim a
        previously unbounded save file down to maxlen."""
        if not isinstance(self.data, OrderedDict):
            self.data = OrderedDict(self.data)
        trimmed = 0
        while self.maxlen > 0 and len(self.data) > self.maxlen:
            self.data.popitem(last=False)
            trimmed += 1
        if trimmed:
            LOG.info(
                f'Trimmed {trimmed} old callsigns from the seen list to maxlen={self.maxlen}'
            )

    def is_enabled(self):
        return CONF.enable_seen_list

    def stats(self, serializable=False):
        """Return the stats for the PacketTrack class."""
        with self.lock:
            if serializable:
                # Convert datetime objects to strings for JSON serialization
                serializable_data = {}
                for callsign, data in self.data.items():
                    serializable_data[callsign] = data.copy()
                    if 'last' in serializable_data[callsign] and isinstance(
                        serializable_data[callsign]['last'], datetime.datetime
                    ):
                        serializable_data[callsign]['last'] = serializable_data[
                            callsign
                        ]['last'].isoformat()
                return serializable_data
            else:
                return self.data

    def rx(self, packet: type[core.Packet]):
        """When we get a packet from the network, update the seen list."""
        with self.lock:
            # flush()/a corrupt save file replace data with a plain dict.
            self._restore_ordereddict()
            callsign = None
            if packet.from_call:
                callsign = packet.from_call
            else:
                LOG.warning(f"Can't find FROM in packet {packet}")
                return
            if callsign not in self.data:
                # Cap as LRU like PacketList does: OrderedDict keys keep
                # insertion order, so pop the least recently seen on overflow.
                if self.maxlen > 0 and len(self.data) >= self.maxlen:
                    self.data.popitem(last=False)
                self.data[callsign] = {
                    'last': None,
                    'count': 0,
                }
            else:
                self.data.move_to_end(callsign)
            self.data[callsign]['last'] = datetime.datetime.now()
            self.data[callsign]['count'] += 1

    def tx(self, packet: type[core.Packet]):
        """We don't care about TX packets."""
