import logging
import time

from aprsd import plugin
from aprsd.utils import trace


LOG = logging.getLogger("APRSD")


class PingPlugin(plugin.APRSDRegexCommandPluginBase):
    """Ping."""

    command_regex = r"^([p]|[p]\s|ping)"
    command_name = "ping"
    short_description = "reply with a Pong!"

    @trace.trace
    def process(self, packet):
        LOG.info("PingPlugin")
        # fromcall = packet.get("from")
        # message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")
        stm = time.localtime()
        h = stm.tm_hour
        m = stm.tm_min
        s = stm.tm_sec
        reply = (
            "Pong! " + str(h).zfill(2) + ":" + str(m).zfill(2) + ":" + str(s).zfill(2)
        )
        return reply.rstrip()
