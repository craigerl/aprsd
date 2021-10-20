import datetime
import logging
import threading

import aprsd
from aprsd import packets, plugin, utils


LOG = logging.getLogger("APRSD")


class APRSDStats:

    _instance = None
    lock = None
    config = None

    start_time = None
    _aprsis_server = None
    _aprsis_keepalive = None

    _msgs_tracked = 0
    _msgs_tx = 0
    _msgs_rx = 0

    _msgs_mice_rx = 0

    _ack_tx = 0
    _ack_rx = 0

    _email_thread_last_time = None
    _email_tx = 0
    _email_rx = 0

    _mem_current = 0
    _mem_peak = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # any initializetion here
            cls._instance.lock = threading.Lock()
            cls._instance.start_time = datetime.datetime.now()
            cls._instance._aprsis_keepalive = datetime.datetime.now()
        return cls._instance

    def __init__(self, config=None):
        if config:
            self.config = config

    @property
    def uptime(self):
        with self.lock:
            return datetime.datetime.now() - self.start_time

    @property
    def memory(self):
        with self.lock:
            return self._mem_current

    def set_memory(self, memory):
        with self.lock:
            self._mem_current = memory

    @property
    def memory_peak(self):
        with self.lock:
            return self._mem_peak

    def set_memory_peak(self, memory):
        with self.lock:
            self._mem_peak = memory

    @property
    def aprsis_server(self):
        with self.lock:
            return self._aprsis_server

    def set_aprsis_server(self, server):
        with self.lock:
            self._aprsis_server = server

    @property
    def aprsis_keepalive(self):
        with self.lock:
            return self._aprsis_keepalive

    def set_aprsis_keepalive(self):
        with self.lock:
            self._aprsis_keepalive = datetime.datetime.now()

    @property
    def msgs_tx(self):
        with self.lock:
            return self._msgs_tx

    def msgs_tx_inc(self):
        with self.lock:
            self._msgs_tx += 1

    @property
    def msgs_rx(self):
        with self.lock:
            return self._msgs_rx

    def msgs_rx_inc(self):
        with self.lock:
            self._msgs_rx += 1

    @property
    def msgs_mice_rx(self):
        with self.lock:
            return self._msgs_mice_rx

    def msgs_mice_inc(self):
        with self.lock:
            self._msgs_mice_rx += 1

    @property
    def ack_tx(self):
        with self.lock:
            return self._ack_tx

    def ack_tx_inc(self):
        with self.lock:
            self._ack_tx += 1

    @property
    def ack_rx(self):
        with self.lock:
            return self._ack_rx

    def ack_rx_inc(self):
        with self.lock:
            self._ack_rx += 1

    @property
    def msgs_tracked(self):
        with self.lock:
            return self._msgs_tracked

    def msgs_tracked_inc(self):
        with self.lock:
            self._msgs_tracked += 1

    @property
    def email_tx(self):
        with self.lock:
            return self._email_tx

    def email_tx_inc(self):
        with self.lock:
            self._email_tx += 1

    @property
    def email_rx(self):
        with self.lock:
            return self._email_rx

    def email_rx_inc(self):
        with self.lock:
            self._email_rx += 1

    @property
    def email_thread_time(self):
        with self.lock:
            return self._email_thread_last_time

    def email_thread_update(self):
        with self.lock:
            self._email_thread_last_time = datetime.datetime.now()

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

        stats = {
            "aprsd": {
                "version": aprsd.__version__,
                "uptime": utils.strfdelta(self.uptime),
                "memory_current": self.memory,
                "memory_current_str": utils.human_size(self.memory),
                "memory_peak": self.memory_peak,
                "memory_peak_str": utils.human_size(self.memory_peak),
                "watch_list": wl.get_all(),
                "seen_list": sl.get_all(),
            },
            "aprs-is": {
                "server": self.aprsis_server,
                "callsign": self.config["aprs"]["login"],
                "last_update": last_aprsis_keepalive,
            },
            "messages": {
                "tracked": self.msgs_tracked,
                "sent": self.msgs_tx,
                "recieved": self.msgs_rx,
                "ack_sent": self.ack_tx,
                "ack_recieved": self.ack_rx,
                "mic-e recieved": self.msgs_mice_rx,
            },
            "email": {
                "enabled": self.config["aprsd"]["email"]["enabled"],
                "sent": self._email_tx,
                "recieved": self._email_rx,
                "thread_last_update": last_update,
            },
            "plugins": plugin_stats,
        }
        return stats

    def __str__(self):
        return (
            "Uptime:{} Msgs TX:{} RX:{} "
            "ACK: TX:{} RX:{} "
            "Email TX:{} RX:{} LastLoop:{} ".format(
                self.uptime,
                self._msgs_tx,
                self._msgs_rx,
                self._ack_tx,
                self._ack_rx,
                self._email_tx,
                self._email_rx,
                self._email_thread_last_time,
            )
        )
