import logging

from aprsd import plugin


LOG = logging.getLogger("APRSD")


class HelloPlugin(plugin.APRSDRegexCommandPluginBase):
    """Hello World."""

    version = "1.0"
    # matches any string starting with h or H
    command_regex = "^[hH]"
    command_name = "hello"

    def process(self, packet):
        LOG.info("HelloPlugin")
        reply = f"Hello '{packet.from_call}'"
        return reply
