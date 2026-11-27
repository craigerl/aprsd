import logging

from aprsd import packets, plugin

LOG = logging.getLogger('APRSD')


class HelloPlugin(plugin.APRSDRegexCommandPluginBase):
    """Hello World."""

    version = '1.0'
    # matches the whole first word hello or hi
    command_regex = r'^(hello|hi)\b'
    command_name = 'hello'

    def process(self, packet: packets.MessagePacket):
        LOG.info('HelloPlugin')
        reply = f"Hello '{packet.from_call}'"
        return reply
