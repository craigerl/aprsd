import logging

from ax253 import Frame
import kiss
from oslo_config import cfg

from aprsd import conf  # noqa
from aprsd.packets import core
from aprsd.utils import trace


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class KISS3Client:
    def __init__(self):
        self.setup()

    def is_alive(self):
        return True

    def setup(self):
        # we can be TCP kiss or Serial kiss
        if CONF.kiss_serial.enabled:
            LOG.debug(
                "KISS({}) Serial connection to {}".format(
                    kiss.__version__,
                    CONF.kiss_serial.device,
                ),
            )
            self.kiss = kiss.SerialKISS(
                port=CONF.kiss_serial.device,
                speed=CONF.kiss_serial.baudrate,
                strip_df_start=True,
            )
        elif CONF.kiss_tcp.enabled:
            LOG.debug(
                "KISS({}) TCP Connection to {}:{}".format(
                    kiss.__version__,
                    CONF.kiss_tcp.host,
                    CONF.kiss_tcp.port,
                ),
            )
            self.kiss = kiss.TCPKISS(
                host=CONF.kiss_tcp.host,
                port=CONF.kiss_tcp.port,
                strip_df_start=True,
            )

        LOG.debug("Starting KISS interface connection")
        self.kiss.start()

    @trace.trace
    def stop(self):
        try:
            self.kiss.stop()
            self.kiss.loop.call_soon_threadsafe(
                self.kiss.protocol.transport.close,
            )
        except Exception as ex:
            LOG.exception(ex)

    def set_filter(self, filter):
        # This does nothing right now.
        pass

    def parse_frame(self, frame_bytes):
        try:
            frame = Frame.from_bytes(frame_bytes)
            # Now parse it with aprslib
            kwargs = {
                "frame": frame,
            }
            self._parse_callback(**kwargs)
        except Exception as ex:
            LOG.error("Failed to parse bytes received from KISS interface.")
            LOG.exception(ex)

    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        LOG.debug("Start blocking KISS consumer")
        self._parse_callback = callback
        self.kiss.read(callback=self.parse_frame, min_frames=None)
        LOG.debug("END blocking KISS consumer")

    def send(self, packet):
        """Send an APRS Message object."""

        # payload = (':%-9s:%s' % (
        #     msg.tocall,
        #     payload
        # )).encode('US-ASCII'),
        # payload = str(msg).encode('US-ASCII')
        payload = None
        path = ["WIDE1-1", "WIDE2-1"]
        if isinstance(packet, core.AckPacket):
            msg_payload = f"ack{packet.msgNo}"
        elif isinstance(packet, core.Packet):
            payload = packet.raw.encode("US-ASCII")
            path = ["WIDE2-1"]
        else:
            msg_payload = f"{packet.raw}{{{str(packet.msgNo)}"

        if not payload:
            payload = (
                ":{:<9}:{}".format(
                    packet.to_call,
                    msg_payload,
                )
            ).encode("US-ASCII")

        LOG.debug(f"Send '{payload}' TO KISS")
        frame = Frame.ui(
            destination=packet.to_call,
            source=packet.from_call,
            path=path,
            info=payload,
        )
        self.kiss.write(frame)
