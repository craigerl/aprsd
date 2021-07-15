import logging

import aprsd
from aprsd import plugin, stats, trace

LOG = logging.getLogger("APRSD")


class VersionPlugin(plugin.APRSDMessagePluginBase):
    """Version of APRSD Plugin."""

    version = "1.0"
    command_regex = "^[vV]"
    command_name = "version"

    # message_number:time combos so we don't resend the same email in
    # five mins {int:int}
    email_sent_dict = {}

    @trace.trace
    def command(self, packet):
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
