import logging
import time

from aprsd import packets, plugin

LOG = logging.getLogger('APRSD')


class PingPlugin(plugin.APRSDRegexCommandPluginBase):
    """Ping."""

    command_regex = r'^([p]|[p]\s|ping)'
    command_name = 'ping'
    short_description = 'reply with a Pong!'

    def process(self, packet: packets.MessagePacket) -> str:
        LOG.info('PingPlugin')
        stm = time.localtime()
        h = stm.tm_hour
        m = stm.tm_min
        s = stm.tm_sec
        reply = (
            'Pong! ' + str(h).zfill(2) + ':' + str(m).zfill(2) + ':' + str(s).zfill(2)
        )
        return reply.rstrip()
