import logging
import time

from aprsd import fuzzyclock, plugin

LOG = logging.getLogger("APRSD")


class TimePlugin(plugin.APRSDPluginBase):
    """Time command."""

    version = "1.0"
    command_regex = "^[tT]"
    command_name = "time"

    def command(self, fromcall, message, ack):
        LOG.info("TIME COMMAND")
        stm = time.localtime()
        h = stm.tm_hour
        m = stm.tm_min
        cur_time = fuzzyclock.fuzzy(h, m, 1)
        reply = "{} ({}:{} PDT) ({})".format(
            cur_time,
            str(h),
            str(m).rjust(2, "0"),
            message.rstrip(),
        )
        return reply
