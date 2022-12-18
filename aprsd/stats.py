import datetime
import logging
import threading

import wrapt

import aprsd
from aprsd import packets, plugin, utils


LOG = logging.getLogger("APRSD")


class APRSDStats:

    _instance = None
    lock = threading.Lock()
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
            cls._instance.start_time = datetime.datetime.now()
            cls._instance._aprsis_keepalive = datetime.datetime.now()
        return cls._instance

    def __init__(self, config=None):
        if config:
            self.config = config

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

    def rx_packet(self, packet):
        if isinstance(packet, packets.MessagePacket):
            self.msgs_rx_inc()
        elif isinstance(packet, packets.MicEPacket):
            self.msgs_mice_inc()
        elif isinstance(packet, packets.AckPacket):
            self.ack_rx_inc()

    @wrapt.synchronized(lock)
    @property
    def msgs_tx(self):
        return self._msgs_tx

    @wrapt.synchronized(lock)
    def msgs_tx_inc(self):
        self._msgs_tx += 1

    @wrapt.synchronized(lock)
    @property
    def msgs_rx(self):
        return self._msgs_rx

    @wrapt.synchronized(lock)
    def msgs_rx_inc(self):
        self._msgs_rx += 1

    @wrapt.synchronized(lock)
    @property
    def msgs_mice_rx(self):
        return self._msgs_mice_rx

    @wrapt.synchronized(lock)
    def msgs_mice_inc(self):
        self._msgs_mice_rx += 1

    @wrapt.synchronized(lock)
    @property
    def ack_tx(self):
        return self._ack_tx

    @wrapt.synchronized(lock)
    def ack_tx_inc(self):
        self._ack_tx += 1

    @wrapt.synchronized(lock)
    @property
    def ack_rx(self):
        return self._ack_rx

    @wrapt.synchronized(lock)
    def ack_rx_inc(self):
        self._ack_rx += 1

    @wrapt.synchronized(lock)
    @property
    def msgs_tracked(self):
        return self._msgs_tracked

    @wrapt.synchronized(lock)
    def msgs_tracked_inc(self):
        self._msgs_tracked += 1

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

        stats = {
            "aprsd": {
                "version": aprsd.__version__,
                "uptime": utils.strfdelta(self.uptime),
                "memory_current": int(self.memory),
                "memory_current_str": utils.human_size(self.memory),
                "memory_peak": int(self.memory_peak),
                "memory_peak_str": utils.human_size(self.memory_peak),
                "watch_list": wl.get_all(),
                "seen_list": sl.get_all(),
            },
            "aprs-is": {
                "server": str(self.aprsis_server),
                "callsign": self.config["aprs"]["login"],
                "last_update": last_aprsis_keepalive,
            },
            "messages": {
                "tracked": int(self.msgs_tracked),
                "sent": int(self.msgs_tx),
                "recieved": int(self.msgs_rx),
                "ack_sent": int(self.ack_tx),
                "ack_recieved": int(self.ack_rx),
                "mic-e recieved": int(self.msgs_mice_rx),
            },
            "email": {
                "enabled": self.config["aprsd"]["email"]["enabled"],
                "sent": int(self._email_tx),
                "recieved": int(self._email_rx),
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
