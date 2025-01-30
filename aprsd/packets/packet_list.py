import logging
from collections import OrderedDict

from oslo_config import cfg

from aprsd.packets import core
from aprsd.utils import objectstore

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class PacketList(objectstore.ObjectStoreMixin):
    """Class to keep track of the packets we tx/rx."""

    _instance = None
    _total_rx: int = 0
    _total_tx: int = 0
    maxlen: int = 100

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.maxlen = CONF.packet_list_maxlen
            cls._instance._init_data()
        return cls._instance

    def _init_data(self):
        self.data = {
            'types': {},
            'packets': OrderedDict(),
        }

    def rx(self, packet: type[core.Packet]):
        """Add a packet that was received."""
        with self.lock:
            self._total_rx += 1
            self._add(packet)
            ptype = packet.__class__.__name__
            type_stats = self.data['types'].setdefault(
                ptype,
                {'tx': 0, 'rx': 0},
            )
            type_stats['rx'] += 1

    def tx(self, packet: type[core.Packet]):
        """Add a packet that was received."""
        with self.lock:
            self._total_tx += 1
            self._add(packet)
            ptype = packet.__class__.__name__
            type_stats = self.data['types'].setdefault(
                ptype,
                {'tx': 0, 'rx': 0},
            )
            type_stats['tx'] += 1

    def add(self, packet):
        with self.lock:
            self._add(packet)

    def _add(self, packet):
        if not self.data.get('packets'):
            self._init_data()
        if packet.key in self.data['packets']:
            self.data['packets'].move_to_end(packet.key)
        elif len(self.data['packets']) == self.maxlen:
            self.data['packets'].popitem(last=False)
        self.data['packets'][packet.key] = packet

    def find(self, packet):
        with self.lock:
            return self.data['packets'][packet.key]

    def __len__(self):
        with self.lock:
            return len(self.data['packets'])

    def total_rx(self):
        with self.lock:
            return self._total_rx

    def total_tx(self):
        with self.lock:
            return self._total_tx

    def stats(self, serializable=False) -> dict:
        with self.lock:
            # Get last N packets directly using list slicing
            if CONF.packet_list_stats_maxlen >= 0:
                packets_list = list(self.data.get('packets', {}).values())
                pkts = packets_list[-CONF.packet_list_stats_maxlen :][::-1]
            else:
                # We have to copy here, because this get() results in a pointer
                # to the packets internally here, which can change after this
                # function returns, which would cause a problem trying to save
                # the stats to disk.
                pkts = self.data.get('packets', {}).copy()
            stats = {
                'total_tracked': self._total_rx
                + self._total_tx,  # Fixed typo: was rx + rx
                'rx': self._total_rx,
                'tx': self._total_tx,
                'types': self.data.get('types', {}),  # Changed default from [] to {}
                'packet_count': len(self.data.get('packets', [])),
                'maxlen': self.maxlen,
                'packets': pkts,
            }
            return stats
