import logging

from aprsd import packets, plugin


LOG = logging.getLogger("APRSD")


class NotifySeenPlugin(plugin.APRSDWatchListPluginBase):
    """Notification plugin to send seen message for callsign.


    This plugin will track callsigns in the watch list and report
    when a callsign has been seen when the last time they were
    seen was older than the configured age limit.
    """

    short_description = "Notify me when a CALLSIGN is recently seen on APRS-IS"

    def process(self, packet):
        LOG.info("NotifySeenPlugin")

        notify_callsign = self.config["aprsd"]["watch_list"]["alert_callsign"]
        fromcall = packet.get("from")

        wl = packets.WatchList()
        age = wl.age(fromcall)

        if wl.is_old(packet["from"]):
            LOG.info(
                "NOTIFY {} last seen {} max age={}".format(
                    fromcall,
                    age,
                    wl.max_delta(),
                ),
            )
            packet_type = packets.get_packet_type(packet)
            # we shouldn't notify the alert user that they are online.
            if fromcall != notify_callsign:
                return f"{fromcall} was just seen by type:'{packet_type}'"
        else:
            LOG.debug(
                "Not old enough to notify callsign '{}' : {} < {}".format(
                    fromcall,
                    age,
                    wl.max_delta(),
                ),
            )
