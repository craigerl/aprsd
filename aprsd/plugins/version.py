import logging

import aprsd
from aprsd import conf, packets, plugin
from aprsd.stats import collector

LOG = logging.getLogger('APRSD')


class VersionPlugin(plugin.APRSDRegexCommandPluginBase):
    """Version of APRSD Plugin."""

    command_regex = r'^([v]|[v]\s|version)'
    command_name = 'version'
    short_description = 'What is the APRSD Version'

    # message_number:time combos so we don't resend the same email in
    # five mins {int:int}
    email_sent_dict = {}

    def process(self, packet: packets.MessagePacket) -> str:
        LOG.info('VersionPlugin')
        s = collector.Collector().collect()
        owner = conf.CONF.owner_callsign or '-'
        return 'APRSD ver:{} uptime:{} owner:{}'.format(
            aprsd.__version__,
            s['APRSDStats']['uptime'],
            owner,
        )
