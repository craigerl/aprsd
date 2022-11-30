import logging

import aprslib
from ax253 import Frame
import kiss

from aprsd import messaging
from aprsd.utils import trace


LOG = logging.getLogger("APRSD")


class KISS3Client:
    def __init__(self, config):
        self.config = config
        self.setup()

    def setup(self):
        # we can be TCP kiss or Serial kiss
        if "serial" in self.config["kiss"] and self.config["kiss"]["serial"].get(
            "enabled",
            False,
        ):
            LOG.debug(
                "KISS({}) Serial connection to {}".format(
                    kiss.__version__,
                    self.config["kiss"]["serial"]["device"],
                ),
            )
            self.kiss = kiss.SerialKISS(
                port=self.config["kiss"]["serial"]["device"],
                speed=self.config["kiss"]["serial"].get("baudrate", 9600),
                strip_df_start=True,
            )
        elif "tcp" in self.config["kiss"] and self.config["kiss"]["tcp"].get(
            "enabled",
            False,
        ):
            LOG.debug(
                "KISS({}) TCP Connection to {}:{}".format(
                    kiss.__version__,
                    self.config["kiss"]["tcp"]["host"],
                    self.config["kiss"]["tcp"]["port"],
                ),
            )
            self.kiss = kiss.TCPKISS(
                host=self.config["kiss"]["tcp"]["host"],
                port=int(self.config["kiss"]["tcp"]["port"]),
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
        frame = Frame.from_bytes(frame_bytes)
        # Now parse it with aprslib
        packet = aprslib.parse(str(frame))
        kwargs = {
            "frame": str(frame),
            "packet": packet,
        }
        self._parse_callback(**kwargs)

    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        LOG.debug("Start blocking KISS consumer")
        self._parse_callback = callback
        self.kiss.read(callback=self.parse_frame, min_frames=None)
        LOG.debug("END blocking KISS consumer")

    def send(self, msg):
        """Send an APRS Message object."""

        # payload = (':%-9s:%s' % (
        #     msg.tocall,
        #     payload
        # )).encode('US-ASCII'),
        # payload = str(msg).encode('US-ASCII')
        payload = None
        path = ["WIDE1-1", "WIDE2-1"]
        if isinstance(msg, messaging.AckMessage):
            msg_payload = f"ack{msg.id}"
        elif isinstance(msg, messaging.RawMessage):
            payload = msg.message.encode("US-ASCII")
            path = ["WIDE2-1"]
        else:
            msg_payload = f"{msg.message}{{{str(msg.id)}"

        if not payload:
            payload = (
                ":{:<9}:{}".format(
                    msg.tocall,
                    msg_payload,
                )
            ).encode("US-ASCII")

        LOG.debug(f"Send '{payload}' TO KISS")
        frame = Frame.ui(
            destination=msg.tocall,
            source=msg.fromcall,
            path=path,
            info=payload,
        )
        self.kiss.write(frame)
