import logging
import threading
from typing import Callable

import timeago
import wrapt
from loguru import logger
from oslo_config import cfg

from aprsd.client import drivers  # noqa - ensure drivers are registered
from aprsd.client.drivers.registry import DriverRegistry
from aprsd.packets import core
from aprsd.utils import keepalive_collector

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')
LOGU = logger


class APRSDClient:
    """APRSD client class.

    This is a singleton class that provides a single instance of the APRSD client.
    It is responsible for connecting to the appropriate APRSD client driver based on
    the configuration.

    """

    _instance = None
    driver = None
    lock = threading.Lock()
    filter = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            keepalive_collector.KeepAliveCollector().register(cls)
        return cls._instance

    def __init__(self):
        self.connected = False
        self.login_status = {
            'success': False,
            'message': None,
        }
        if not self.driver:
            self.driver = DriverRegistry().get_driver()
            self.driver.setup_connection()

    def stats(self, serializable=False) -> dict:
        stats = {}
        if self.driver:
            stats = self.driver.stats(serializable=serializable)
        return stats

    @property
    def is_enabled(self):
        if not self.driver:
            return False
        return self.driver.is_enabled()

    @property
    def is_configured(self):
        if not self.driver:
            return False
        return self.driver.is_configured()

    # @property
    # def is_connected(self):
    #     if not self.driver:
    #         return False
    #     return self.driver.is_connected()

    @property
    def login_success(self):
        if not self.driver:
            return False
        return self.driver.login_success

    @property
    def login_failure(self):
        if not self.driver:
            return None
        return self.driver.login_failure

    def set_filter(self, filter):
        self.filter = filter
        if not self.driver:
            return
        self.driver.set_filter(filter)

    def get_filter(self):
        if not self.driver:
            return None
        return self.driver.filter

    def is_alive(self):
        return self.driver.is_alive()

    def close(self):
        if not self.driver:
            return
        self.driver.close()

    @wrapt.synchronized(lock)
    def reset(self):
        """Call this to force a rebuild/reconnect."""
        LOG.info('Resetting client connection.')
        if self.driver:
            self.driver.close()
            self.driver.setup_connection()
            if self.filter:
                self.driver.set_filter(self.filter)
        else:
            LOG.warning('Client not initialized, nothing to reset.')

    def send(self, packet: core.Packet) -> bool:
        return self.driver.send(packet)

    # For the keepalive collector
    def keepalive_check(self):
        # Don't check the first time through.
        if not self.driver.is_alive and self._checks:
            LOG.warning("Resetting client.  It's not alive.")
            self.reset()
        self._checks = True

    # For the keepalive collector
    def keepalive_log(self):
        if ka := self.driver.keepalive:
            keepalive = timeago.format(ka)
        else:
            keepalive = 'N/A'
        LOGU.opt(colors=True).info(f'<green>Client keepalive {keepalive}</green>')

    def consumer(self, callback: Callable, raw: bool = False):
        return self.driver.consumer(callback=callback, raw=raw)

    def decode_packet(self, *args, **kwargs) -> core.Packet:
        return self.driver.decode_packet(*args, **kwargs)
