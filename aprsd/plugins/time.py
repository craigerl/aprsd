import logging

import pytz
from oslo_config import cfg
from tzlocal import get_localzone

from aprsd import packets, plugin
from aprsd.utils import fuzzy

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class TimePlugin(plugin.APRSDRegexCommandPluginBase):
    """Time command."""

    # Look for t or t<space> or T<space> or time
    command_regex = r'^([t]|[t]\s|time)'
    command_name = 'time'
    short_description = 'What is the current local time.'

    def _get_local_tz(self):
        lz = get_localzone()
        return pytz.timezone(str(lz))

    def _get_utcnow(self):
        return pytz.datetime.datetime.utcnow()

    def build_date_str(self, localzone):
        utcnow = self._get_utcnow()
        gmt_t = pytz.utc.localize(utcnow)
        local_t = gmt_t.astimezone(localzone)

        local_short_str = local_t.strftime('%H:%M %Z')
        local_hour = local_t.strftime('%H')
        local_min = local_t.strftime('%M')
        cur_time = fuzzy(int(local_hour), int(local_min), 1)

        reply = '{} ({})'.format(
            cur_time,
            local_short_str,
        )

        return reply

    def process(self, packet: packets.MessagePacket) -> str:
        LOG.info('TimePlugin')
        # So we can mock this in unit tests
        localzone = self._get_local_tz()
        return self.build_date_str(localzone)
