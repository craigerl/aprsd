import logging

from aprsd import plugin


LOG = logging.getLogger("APRSD")


class HelloPlugin(plugin.APRSDPluginBase):
    """Hello World."""

    version = "1.0"
    # matches any string starting with h or H
    command_regex = "^[hH]"
    command_name = "hello"

    def command(self, fromcall, message, ack):
        LOG.info("HelloPlugin")
        reply = f"Hello '{fromcall}'"
        return reply
