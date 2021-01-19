import logging
import time

from aprsd import fuzzyclock, plugin
import pytz

LOG = logging.getLogger("APRSD")


class TimePlugin(plugin.APRSDPluginBase):
    """Time command."""

    version = "1.0"
    command_regex = "^[tT]"
    command_name = "time"

    def _get_local_tz(self):
        return pytz.timezone(time.strftime("%Z"))

    def _get_utcnow(self):
        return pytz.datetime.datetime.utcnow()

    def command(self, fromcall, message, ack):
        LOG.info("TIME COMMAND")
        # So we can mock this in unit tests
        localzone = self._get_local_tz()

        # This is inefficient for now, but this enables
        # us to add the ability to provide time in the TZ
        # of the caller, if we can get the TZ from their callsign location
        # This also accounts for running aprsd in different timezones
        utcnow = self._get_utcnow()
        gmt_t = pytz.utc.localize(utcnow)
        local_t = gmt_t.astimezone(localzone)

        local_short_str = local_t.strftime("%H:%M %Z")
        local_hour = local_t.strftime("%H")
        local_min = local_t.strftime("%M")
        cur_time = fuzzyclock.fuzzy(int(local_hour), int(local_min), 1)

        reply = "{} ({}) ({})".format(
            cur_time,
            local_short_str,
            message.rstrip(),
        )

        return reply
