import logging
import time

from aprsd import plugin, trace

LOG = logging.getLogger("APRSD")


class PingPlugin(plugin.APRSDMessagePluginBase):
    """Ping."""

    version = "1.0"
    command_regex = "^[pP]"
    command_name = "ping"

    @trace.trace
    def command(self, packet):
        LOG.info("PINGPlugin")
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
