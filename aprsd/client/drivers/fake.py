import datetime
import logging
import threading
import time
from typing import Callable

import aprslib
import wrapt
from oslo_config import cfg

from aprsd import conf  # noqa
from aprsd.packets import core
from aprsd.utils import trace

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class APRSDFakeDriver(metaclass=trace.TraceWrapperMetaclass):
    """Fake client for testing."""

    # flag to tell us to stop
    thread_stop = False

    # date for last time we heard from the server
    aprsd_keepalive = datetime.datetime.now()

    lock = threading.Lock()
    path = []

    def __init__(self):
        LOG.info('Starting APRSDFakeDriver driver.')
        self.path = ['WIDE1-1', 'WIDE2-1']

    @staticmethod
    def is_enabled():
        if CONF.fake_client.enabled:
            return True
        return False

    @staticmethod
    def is_configured():
        return APRSDFakeDriver.is_enabled

    def is_alive(self):
        """If the connection is alive or not."""
        return not self.thread_stop

    def close(self):
        self.thread_stop = True
        LOG.info('Shutdown APRSDFakeDriver driver.')

    def setup_connection(self):
        # It's fake....
        pass

    def set_filter(self, filter: str) -> None:
        pass

    def login_success(self) -> bool:
        return True

    def login_failure(self) -> str:
        return None

    @wrapt.synchronized(lock)
    def send(self, packet: core.Packet):
        """Send an APRS Message object."""
        LOG.info(f'Sending packet: {packet}')
        payload = None
        if isinstance(packet, core.Packet):
            packet.prepare()
            payload = packet.payload.encode('US-ASCII')
        else:
            msg_payload = f'{packet.raw}{{{str(packet.msgNo)}'
            payload = (
                ':{:<9}:{}'.format(
                    packet.to_call,
                    msg_payload,
                )
            ).encode('US-ASCII')

        LOG.debug(
            f"FAKE::Send '{payload}' TO '{packet.to_call}' From "
            f'\'{packet.from_call}\' with PATH "{self.path}"',
        )

    def consumer(self, callback: Callable, raw: bool = False):
        LOG.debug('Start non blocking FAKE consumer')
        # Generate packets here?
        raw_str = 'GTOWN>APDW16,WIDE1-1,WIDE2-1:}KM6LYW-9>APZ100,TCPIP,GTOWN*::KM6LYW   :KM6LYW: 19 Miles SW'
        self.aprsd_keepalive = datetime.datetime.now()
        if raw:
            callback(raw=raw_str)
        else:
            pkt_raw = aprslib.parse(raw_str)
            pkt = core.factory(pkt_raw)
            callback(packet=pkt)

        LOG.debug(f'END blocking FAKE consumer {self}')
        time.sleep(1)

    def decode_packet(self, *args, **kwargs):
        """APRS lib already decodes this."""
        if not kwargs:
            return None

        if kwargs.get('packet'):
            return kwargs.get('packet')

        if kwargs.get('raw'):
            pkt_raw = aprslib.parse(kwargs.get('raw'))
            pkt = core.factory(pkt_raw)
            return pkt

    def stats(self, serializable: bool = False) -> dict:
        return {
            'driver': self.__class__.__name__,
            'is_alive': self.is_alive(),
            'transport': 'fake',
        }
