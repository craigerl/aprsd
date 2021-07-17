import logging

from aprsd import messaging, packets, plugin

LOG = logging.getLogger("APRSD")


class NotifySeenPlugin(plugin.APRSDNotificationPluginBase):
    """Notification plugin to send seen message for callsign.


    This plugin will track callsigns in the watch list and report
    when a callsign has been seen when the last time they were
    seen was older than the configured age limit.
    """

    version = "1.0"

    def __init__(self, config):
        """The aprsd config object is stored."""
        super().__init__(config)

    def notify(self, packet):
        LOG.info("BaseNotifyPlugin")

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
                return "{} was just seen by type:'{}'".format(fromcall, packet_type)
        else:
            LOG.debug(
                "Not old enough to notify callsign '{}' : {} < {}".format(
                    fromcall,
                    age,
                    wl.max_delta(),
                ),
            )
            return messaging.NULL_MESSAGE
