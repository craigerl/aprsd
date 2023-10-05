import logging
import threading
import time

import aprslib
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
    path = []

    def __init__(self):
        LOG.info("Starting APRSDFakeClient client.")
        self.path = ["WIDE1-1", "WIDE2-1"]

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
        payload = None
        if isinstance(packet, core.Packet):
            packet.prepare()
            payload = packet.payload.encode("US-ASCII")
            if packet.path:
                packet.path
            else:
                self.path
        else:
            msg_payload = f"{packet.raw}{{{str(packet.msgNo)}"
            payload = (
                ":{:<9}:{}".format(
                    packet.to_call,
                    msg_payload,
                )
            ).encode("US-ASCII")

        LOG.debug(
            f"FAKE::Send '{payload}' TO '{packet.to_call}' From "
            f"'{packet.from_call}' with PATH \"{self.path}\"",
        )

    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        LOG.debug("Start non blocking FAKE consumer")
        # Generate packets here?
        raw = "GTOWN>APDW16,WIDE1-1,WIDE2-1:}KM6LYW-9>APZ100,TCPIP,GTOWN*::KM6LYW   :KM6LYW: 19 Miles SW"
        pkt_raw = aprslib.parse(raw)
        pkt = core.Packet.factory(pkt_raw)
        callback(packet=pkt)
        LOG.debug(f"END blocking FAKE consumer {self}")
        time.sleep(8)
