import logging

import aprsd
from aprsd import plugin
from aprsd.stats import collector


LOG = logging.getLogger("APRSD")


class VersionPlugin(plugin.APRSDRegexCommandPluginBase):
    """Version of APRSD Plugin."""

    command_regex = r"^([v]|[v]\s|version)"
    command_name = "version"
    short_description = "What is the APRSD Version"

    # message_number:time combos so we don't resend the same email in
    # five mins {int:int}
    email_sent_dict = {}

    def process(self, packet):
        LOG.info("Version COMMAND")
        # fromcall = packet.get("from")
        # message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")
        s = collector.Collector().collect()
        return "APRSD ver:{} uptime:{}".format(
            aprsd.__version__,
            s["APRSDStats"]["uptime"],
        )
