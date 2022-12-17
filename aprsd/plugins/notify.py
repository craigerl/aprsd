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

    def process(self, packet: packets.MessagePacket):
        LOG.info("NotifySeenPlugin")

        notify_callsign = self.config["aprsd"]["watch_list"]["alert_callsign"]
        fromcall = packet.from_call

        wl = packets.WatchList()
        age = wl.age(fromcall)

        if wl.is_old(fromcall):
            LOG.info(
                "NOTIFY {} last seen {} max age={}".format(
                    fromcall,
                    age,
                    wl.max_delta(),
                ),
            )
            packet_type = packet.__class__.__name__
            # we shouldn't notify the alert user that they are online.
            if fromcall != notify_callsign:
                pkt = packets.MessagePacket(
                    from_call=self.config["aprsd"]["callsign"],
                    to_call=notify_callsign,
                    message_text=(
                        f"{fromcall} was just seen by type:'{packet_type}'"
                    ),
                    allow_delay=False,
                )
                # pkt.allow_delay = False
                return pkt
            else:
                LOG.debug("fromcall and notify_callsign are the same, not notifying")
                return packets.NULL_MESSAGE
        else:
            LOG.debug(
                "Not old enough to notify on callsign '{}' : {} < {}".format(
                    fromcall,
                    age,
                    wl.max_delta(),
                ),
            )
            return packets.NULL_MESSAGE
