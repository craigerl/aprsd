import datetime
import logging
import re

from oslo_config import cfg

from aprsd import packets, plugin
from aprsd.packets import tracker
from aprsd.utils import trace


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class QueryPlugin(plugin.APRSDRegexCommandPluginBase):
    """Query command."""

    command_regex = r"^\!.*"
    command_name = "query"
    short_description = "APRSD Owner command to query messages in the MsgTrack"

    def setup(self):
        """Do any plugin setup here."""
        if not CONF.query_plugin.callsign:
            LOG.error("Config query_plugin.callsign not set.  Disabling plugin")
            self.enabled = False
        self.enabled = True

    @trace.trace
    def process(self, packet: packets.MessagePacket):
        LOG.info("Query COMMAND")

        fromcall = packet.from_call
        message = packet.get("message_text", None)

        pkt_tracker = tracker.PacketTrack()
        now = datetime.datetime.now()
        reply = "Pending messages ({}) {}".format(
            len(pkt_tracker),
            now.strftime("%H:%M:%S"),
        )

        searchstring = "^" + CONF.query_plugin.callsign + ".*"
        # only I can do admin commands
        if re.search(searchstring, fromcall):

            # resend last N most recent:  "!3"
            r = re.search(r"^\!([0-9]).*", message)
            if r is not None:
                if len(pkt_tracker) > 0:
                    last_n = r.group(1)
                    reply = packets.NULL_MESSAGE
                    LOG.debug(reply)
                    pkt_tracker.restart_delayed(count=int(last_n))
                else:
                    reply = "No pending msgs to resend"
                    LOG.debug(reply)
                return reply

            # resend all:   "!a"
            r = re.search(r"^\![aA].*", message)
            if r is not None:
                if len(pkt_tracker) > 0:
                    reply = packets.NULL_MESSAGE
                    LOG.debug(reply)
                    pkt_tracker.restart_delayed()
                else:
                    reply = "No pending msgs"
                    LOG.debug(reply)
                return reply

            # delete all:   "!d"
            r = re.search(r"^\![dD].*", message)
            if r is not None:
                reply = "Deleted ALL pending msgs."
                LOG.debug(reply)
                pkt_tracker.flush()
                return reply

        return reply
