import logging
import threading
import time

from oslo_config import cfg
import wrapt

from aprsd import conf  # noqa
from aprsd.packets import core
from aprsd.utils import trace


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class APRSDFakeClient(metaclass=trace.TraceWrapperMetaclass):
    '''Fake client for testing.'''

    # flag to tell us to stop
    thread_stop = False

    lock = threading.Lock()

    def stop(self):
        self.thread_stop = True
        LOG.info("Shutdown APRSDFakeClient client.")

    def is_alive(self):
        """If the connection is alive or not."""
        return not self.thread_stop

    @wrapt.synchronized(lock)
    def send(self, packet: core.Packet):
        """Send an APRS Message object."""
        LOG.info(f"Sending packet: {packet}")

    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        LOG.debug("Start non blocking FAKE consumer")
        # Generate packets here?
        pkt = core.MessagePacket(
            from_call="N0CALL",
            to_call=CONF.callsign,
            message_text="Hello World",
            msgNo=13,
        )
        callback(packet=pkt)
        LOG.debug(f"END blocking FAKE consumer {self}")
        time.sleep(8)
