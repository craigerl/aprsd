import datetime
import logging
import threading

from oslo_config import cfg
import wrapt

import aprsd
from aprsd import packets, plugin, utils


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class APRSDStats:

    _instance = None
    lock = threading.Lock()

    start_time = None
    _aprsis_server = None
    _aprsis_keepalive = None

    _email_thread_last_time = None
    _email_tx = 0
    _email_rx = 0

    _mem_current = 0
    _mem_peak = 0

    _thread_info = {}

    _pkt_cnt = {
        "Packet": {
            "tx": 0,
            "rx": 0,
        },
        "AckPacket": {
            "tx": 0,
            "rx": 0,
        },
        "GPSPacket": {
            "tx": 0,
            "rx": 0,
        },
        "StatusPacket": {
            "tx": 0,
            "rx": 0,
        },
        "MicEPacket": {
            "tx": 0,
            "rx": 0,
        },
        "MessagePacket": {
            "tx": 0,
            "rx": 0,
        },
        "WeatherPacket": {
            "tx": 0,
            "rx": 0,
        },
        "ObjectPacket": {
            "tx": 0,
            "rx": 0,
        },
    }

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # any init here
            cls._instance.start_time = datetime.datetime.now()
            cls._instance._aprsis_keepalive = datetime.datetime.now()
        return cls._instance

    @wrapt.synchronized(lock)
    @property
    def uptime(self):
        return datetime.datetime.now() - self.start_time

    @wrapt.synchronized(lock)
    @property
    def memory(self):
        return self._mem_current

    @wrapt.synchronized(lock)
    def set_memory(self, memory):
        self._mem_current = memory

    @wrapt.synchronized(lock)
    @property
    def memory_peak(self):
        return self._mem_peak

    @wrapt.synchronized(lock)
    def set_memory_peak(self, memory):
        self._mem_peak = memory

    @wrapt.synchronized(lock)
    def set_thread_info(self, thread_info):
        self._thread_info = thread_info

    @wrapt.synchronized(lock)
    @property
    def thread_info(self):
        return self._thread_info

    @wrapt.synchronized(lock)
    @property
    def aprsis_server(self):
        return self._aprsis_server

    @wrapt.synchronized(lock)
    def set_aprsis_server(self, server):
        self._aprsis_server = server

    @wrapt.synchronized(lock)
    @property
    def aprsis_keepalive(self):
        return self._aprsis_keepalive

    @wrapt.synchronized(lock)
    def set_aprsis_keepalive(self):
        self._aprsis_keepalive = datetime.datetime.now()

    def rx(self, packet):
        pkt_type = packet.__class__.__name__
        if pkt_type not in self._pkt_cnt:
            self._pkt_cnt[pkt_type] = {
                "tx": 0,
                "rx": 0,
            }
        self._pkt_cnt[pkt_type]["rx"] += 1

    def tx(self, packet):
        pkt_type = packet.__class__.__name__
        if pkt_type not in self._pkt_cnt:
            self._pkt_cnt[pkt_type] = {
                "tx": 0,
                "rx": 0,
            }
        self._pkt_cnt[pkt_type]["tx"] += 1

    @wrapt.synchronized(lock)
    @property
    def msgs_tracked(self):
        return packets.PacketTrack().total_tracked

    @wrapt.synchronized(lock)
    @property
    def email_tx(self):
        return self._email_tx

    @wrapt.synchronized(lock)
    def email_tx_inc(self):
        self._email_tx += 1

    @wrapt.synchronized(lock)
    @property
    def email_rx(self):
        return self._email_rx

    @wrapt.synchronized(lock)
    def email_rx_inc(self):
        self._email_rx += 1

    @wrapt.synchronized(lock)
    @property
    def email_thread_time(self):
        return self._email_thread_last_time

    @wrapt.synchronized(lock)
    def email_thread_update(self):
        self._email_thread_last_time = datetime.datetime.now()

    @wrapt.synchronized(lock)
    def stats(self):
        now = datetime.datetime.now()
        if self._email_thread_last_time:
            last_update = str(now - self._email_thread_last_time)
        else:
            last_update = "never"

        if self._aprsis_keepalive:
            last_aprsis_keepalive = str(now - self._aprsis_keepalive)
        else:
            last_aprsis_keepalive = "never"

        pm = plugin.PluginManager()
        plugins = pm.get_plugins()
        plugin_stats = {}
        if plugins:
            def full_name_with_qualname(obj):
                return "{}.{}".format(
                    obj.__class__.__module__,
                    obj.__class__.__qualname__,
                )

            for p in plugins:
                plugin_stats[full_name_with_qualname(p)] = {
                    "enabled": p.enabled,
                    "rx": p.rx_count,
                    "tx": p.tx_count,
                    "version": p.version,
                }

        wl = packets.WatchList()
        sl = packets.SeenList()
        pl = packets.PacketList()

        stats = {
            "aprsd": {
                "version": aprsd.__version__,
                "uptime": utils.strfdelta(self.uptime),
                "callsign": CONF.callsign,
                "memory_current": int(self.memory),
                "memory_current_str": utils.human_size(self.memory),
                "memory_peak": int(self.memory_peak),
                "memory_peak_str": utils.human_size(self.memory_peak),
                "threads": self._thread_info,
                "watch_list": wl.get_all(),
                "seen_list": sl.get_all(),
            },
            "aprs-is": {
                "server": str(self.aprsis_server),
                "callsign": CONF.aprs_network.login,
                "last_update": last_aprsis_keepalive,
            },
            "packets": {
                "total_tracked": int(pl.total_tx() + pl.total_rx()),
                "total_sent": int(pl.total_tx()),
                "total_received": int(pl.total_rx()),
                "by_type": self._pkt_cnt,
            },
            "messages": {
                "sent": self._pkt_cnt["MessagePacket"]["tx"],
                "received": self._pkt_cnt["MessagePacket"]["tx"],
                "ack_sent": self._pkt_cnt["AckPacket"]["tx"],
            },
            "email": {
                "enabled": CONF.email_plugin.enabled,
                "sent": int(self._email_tx),
                "received": int(self._email_rx),
                "thread_last_update": last_update,
            },
            "plugins": plugin_stats,
        }
        return stats

    def __str__(self):
        pl = packets.PacketList()
        return (
            "Uptime:{} Msgs TX:{} RX:{} "
            "ACK: TX:{} RX:{} "
            "Email TX:{} RX:{} LastLoop:{} ".format(
                self.uptime,
                pl.total_tx(),
                pl.total_rx(),
                self._pkt_cnt["AckPacket"]["tx"],
                self._pkt_cnt["AckPacket"]["rx"],
                self._email_tx,
                self._email_rx,
                self._email_thread_last_time,
            )
        )
