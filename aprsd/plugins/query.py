import logging
import re

from aprsd import messaging, plugin

LOG = logging.getLogger("APRSD")


class QueryPlugin(plugin.APRSDPluginBase):
    """Query command."""

    version = "1.0"
    command_regex = r"^\?.*"
    command_name = "query"

    def command(self, fromcall, message, ack):
        LOG.info("Query COMMAND")

        tracker = messaging.MsgTrack()
        reply = "Pending Messages ({})".format(len(tracker))

        searchstring = "^" + self.config["ham"]["callsign"] + ".*"
        # only I can do admin commands
        if re.search(searchstring, fromcall):
            r = re.search(r"^\?[rR].*", message)
            if r is not None:
                if len(tracker) > 0:
                    reply = messaging.NULL_MESSAGE
                    LOG.debug(reply)
                    tracker.restart_delayed()
                else:
                    reply = "No Delayed Msgs"
                    LOG.debug(reply)
                return reply

            r = re.search(r"^\?[dD].*", message)
            if r is not None:
                reply = "Deleted ALL delayed msgs."
                LOG.debug(reply)
                tracker.flush()
                return reply

        return reply
