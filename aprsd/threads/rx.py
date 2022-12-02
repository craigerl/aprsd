import abc
import logging
import time

import aprslib

from aprsd import client, messaging, packets, plugin, stats
from aprsd.threads import APRSDThread


LOG = logging.getLogger("APRSD")


class APRSDRXThread(APRSDThread):
    def __init__(self, msg_queues, config):
        super().__init__("RX_MSG")
        self.msg_queues = msg_queues
        self.config = config
        self._client = client.factory.create()

    def stop(self):
        self.thread_stop = True
        client.factory.create().client.stop()

    def loop(self):

        # setup the consumer of messages and block until a messages
        try:
            # This will register a packet consumer with aprslib
            # When new packets come in the consumer will process
            # the packet

            # Do a partial here because the consumer signature doesn't allow
            # For kwargs to be passed in to the consumer func we declare
            # and the aprslib developer didn't want to allow a PR to add
            # kwargs.  :(
            # https://github.com/rossengeorgiev/aprs-python/pull/56
            self._client.client.consumer(
                self.process_packet, raw=False, blocking=False,
            )

        except (
            aprslib.exceptions.ConnectionDrop,
            aprslib.exceptions.ConnectionError,
        ):
            LOG.error("Connection dropped, reconnecting")
            time.sleep(5)
            # Force the deletion of the client object connected to aprs
            # This will cause a reconnect, next time client.get_client()
            # is called
            self._client.reset()
        # Continue to loop
        return True

    @abc.abstractmethod
    def process_packet(self, *args, **kwargs):
        pass


class APRSDPluginRXThread(APRSDRXThread):
    """Process received packets.

    This is the main APRSD Server command thread that
    receives packets from APRIS and then sends them for
    processing in the PluginProcessPacketThread.
    """
    def process_packet(self, *args, **kwargs):
        packet = self._client.decode_packet(*args, **kwargs)
        thread = APRSDPluginProcessPacketThread(
            config=self.config,
            packet=packet,
        )
        thread.start()


class APRSDProcessPacketThread(APRSDThread):
    """Base class for processing received packets.

    This is the base class for processing packets coming from
    the consumer.  This base class handles sending ack packets and
    will ack a message before sending the packet to the subclass
    for processing."""

    def __init__(self, config, packet):
        self.config = config
        self.packet = packet
        name = self.packet["raw"][:10]
        super().__init__(f"RXPKT-{name}")

    def process_ack_packet(self, packet):
        ack_num = packet.get("msgNo")
        LOG.info(f"Got ack for message {ack_num}")
        messaging.log_message(
            "RXACK",
            packet["raw"],
            None,
            ack=ack_num,
            fromcall=packet["from"],
        )
        tracker = messaging.MsgTrack()
        tracker.remove(ack_num)
        stats.APRSDStats().ack_rx_inc()
        return

    def loop(self):
        """Process a packet received from aprs-is server."""
        packet = self.packet
        packets.PacketList().add(packet)

        fromcall = packet["from"]
        tocall = packet.get("addresse", None)
        msg = packet.get("message_text", None)
        msg_id = packet.get("msgNo", "0")
        msg_response = packet.get("response", None)
        # LOG.debug(f"Got packet from '{fromcall}' - {packet}")

        # We don't put ack packets destined for us through the
        # plugins.
        if (
            tocall
            and tocall.lower() == self.config["aprsd"]["callsign"].lower()
            and msg_response == "ack"
        ):
            self.process_ack_packet(packet)
        else:
            # It's not an ACK for us, so lets run it through
            # the plugins.
            messaging.log_message(
                "Received Message",
                packet["raw"],
                msg,
                fromcall=fromcall,
                msg_num=msg_id,
            )

            # Only ack messages that were sent directly to us
            if (
                tocall
                and tocall.lower() == self.config["aprsd"]["callsign"].lower()
            ):
                stats.APRSDStats().msgs_rx_inc()
                # let any threads do their thing, then ack
                # send an ack last
                ack = messaging.AckMessage(
                    self.config["aprsd"]["callsign"],
                    fromcall,
                    msg_id=msg_id,
                )
                ack.send()

                self.process_non_ack_packet(packet)
            else:
                LOG.info("Packet was not for us.")
    LOG.debug("Packet processing complete")

    @abc.abstractmethod
    def process_non_ack_packet(self, *args, **kwargs):
        """Ack packets already dealt with here."""


class APRSDPluginProcessPacketThread(APRSDProcessPacketThread):
    """Process the packet through the plugin manager.

    This is the main aprsd server plugin processing thread."""

    def process_non_ack_packet(self, packet):
        """Send the packet through the plugins."""
        fromcall = packet["from"]
        tocall = packet.get("addresse", None)
        msg = packet.get("message_text", None)
        packet.get("msgNo", "0")
        packet.get("response", None)
        pm = plugin.PluginManager()
        try:
            results = pm.run(packet)
            wl = packets.WatchList()
            wl.update_seen(packet)
            replied = False
            for reply in results:
                if isinstance(reply, list):
                    # one of the plugins wants to send multiple messages
                    replied = True
                    for subreply in reply:
                        LOG.debug(f"Sending '{subreply}'")
                        if isinstance(subreply, messaging.Message):
                            subreply.send()
                        else:
                            msg = messaging.TextMessage(
                                self.config["aprsd"]["callsign"],
                                fromcall,
                                subreply,
                            )
                            msg.send()
                elif isinstance(reply, messaging.Message):
                    # We have a message based object.
                    LOG.debug(f"Sending '{reply}'")
                    reply.send()
                    replied = True
                else:
                    replied = True
                    # A plugin can return a null message flag which signals
                    # us that they processed the message correctly, but have
                    # nothing to reply with, so we avoid replying with a
                    # usage string
                    if reply is not messaging.NULL_MESSAGE:
                        LOG.debug(f"Sending '{reply}'")

                        msg = messaging.TextMessage(
                            self.config["aprsd"]["callsign"],
                            fromcall,
                            reply,
                        )
                        msg.send()

            # If the message was for us and we didn't have a
            # response, then we send a usage statement.
            if tocall == self.config["aprsd"]["callsign"] and not replied:
                LOG.warning("Sending help!")
                msg = messaging.TextMessage(
                    self.config["aprsd"]["callsign"],
                    fromcall,
                    "Unknown command! Send 'help' message for help",
                )
                msg.send()
        except Exception as ex:
            LOG.error("Plugin failed!!!")
            LOG.exception(ex)
            # Do we need to send a reply?
            if tocall == self.config["aprsd"]["callsign"]:
                reply = "A Plugin failed! try again?"
                msg = messaging.TextMessage(
                    self.config["aprsd"]["callsign"],
                    fromcall,
                    reply,
                )
                msg.send()
