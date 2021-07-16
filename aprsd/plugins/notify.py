import logging

from aprsd import packets, plugin, trace

LOG = logging.getLogger("APRSD")


class BaseNotifyPlugin(plugin.APRSDNotificationPluginBase):
    """Notification base plugin."""

    version = "1.0"

    @trace.trace
    def notify(self, packet):
        LOG.info("BaseNotifyPlugin")

        notify_callsign = self.config["aprsd"]["watch_list"]["alert_callsign"]
        fromcall = packet.get("from")

        packet_type = packets.get_packet_type(packet)
        # we shouldn't notify the alert user that they are online.
        if fromcall != notify_callsign:
            return "{} was just seen by type:'{}'".format(fromcall, packet_type)
