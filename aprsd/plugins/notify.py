import logging

from aprsd import messaging, packets, plugin, trace


LOG = logging.getLogger("APRSD")


class NotifySeenPlugin(plugin.APRSDWatchListPluginBase):
    """Notification plugin to send seen message for callsign.


    This plugin will track callsigns in the watch list and report
    when a callsign has been seen when the last time they were
    seen was older than the configured age limit.
    """

    short_description = "Notify me when a CALLSIGN is recently seen on APRS-IS"

    @trace.trace
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
                msg = messaging.TextMessage(
                    self.config["aprs"]["login"],
                    notify_callsign,
                    f"{fromcall} was just seen by type:'{packet_type}'",
                    # We don't need to keep this around if it doesn't go thru
                    allow_delay=False,
                )
                return msg
            else:
                LOG.debug("fromcall and notify_callsign are the same, not notifying")
                return messaging.NULL_MESSAGE
        else:
            LOG.debug(
                "Not old enough to notify on callsign '{}' : {} < {}".format(
                    fromcall,
                    age,
                    wl.max_delta(),
                ),
            )
            return messaging.NULL_MESSAGE
