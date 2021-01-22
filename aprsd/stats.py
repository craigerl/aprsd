import datetime
import logging
import threading

LOG = logging.getLogger("APRSD")


class APRSDStats:

    _instance = None
    lock = None
    config = None

    start_time = None

    _msgs_tracked = 0
    _msgs_tx = 0
    _msgs_rx = 0

    _msgs_mice_rx = 0

    _ack_tx = 0
    _ack_rx = 0

    _email_thread_last_time = None
    _email_tx = 0
    _email_rx = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # any initializetion here
            cls._instance.lock = threading.Lock()
            cls._instance.start_time = datetime.datetime.now()
        return cls._instance

    def __init__(self, config=None):
        if config:
            self.config = config

    @property
    def uptime(self):
        with self.lock:
            return str(datetime.datetime.now() - self.start_time)

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
        stats = {
            "messages": {
                "tracked": self.msgs_tracked,
                "sent": self.msgs_tx,
                "recieved": self.msgs_rx,
                "ack_sent": self.ack_tx,
                "ack_recieved": self.ack_rx,
                "mic-e recieved": self.msgs_mice_rx,
            },
            "email": {
                "sent": self._email_tx,
                "recieved": self._email_rx,
                "thread_last_update": str(now - self._email_thread_last_time),
            },
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
