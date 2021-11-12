import logging

import aprsd
from aprsd import plugin, stats, trace


LOG = logging.getLogger("APRSD")


class VersionPlugin(plugin.APRSDRegexCommandPluginBase):
    """Version of APRSD Plugin."""

    command_regex = "^[vV]"
    command_name = "version"
    short_description = "What is the APRSD Version"

    # message_number:time combos so we don't resend the same email in
    # five mins {int:int}
    email_sent_dict = {}

    @trace.trace
    def process(self, packet):
        LOG.info("Version COMMAND")
        # fromcall = packet.get("from")
        # message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")
        stats_obj = stats.APRSDStats()
        s = stats_obj.stats()
        return "APRSD ver:{} uptime:{}".format(
            aprsd.__version__,
            s["aprsd"]["uptime"],
        )
