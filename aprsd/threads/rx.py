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
        # LOG.debug(raw)
        #packet = packets.Packet.factory(raw.copy())
        packet.log(header="RX Packet")
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
        name = self.packet.raw[:10]
        super().__init__(f"RXPKT-{name}")
        self._loop_cnt = 1

    def process_ack_packet(self, packet):
        ack_num = packet.msgNo
        LOG.info(f"Got ack for message {ack_num}")
        packet.log("RXACK")
        pkt_tracker = packets.PacketTrack()
        pkt_tracker.remove(ack_num)
        stats.APRSDStats().ack_rx_inc()
        return

    def loop(self):
        """Process a packet received from aprs-is server."""
        LOG.debug(f"RXPKT-LOOP {self._loop_cnt}")
        packet = self.packet
        packets.PacketList().add(packet)
        our_call = self.config["aprsd"]["callsign"].lower()

        from_call = packet.from_call
        if packet.addresse:
            to_call = packet.addresse
        else:
            to_call = packet.to_call
        msg_id = packet.msgNo

        # We don't put ack packets destined for us through the
        # plugins.
        wl = packets.WatchList()
        wl.update_seen(packet)
        if (
            isinstance(packet, packets.AckPacket)
            and packet.addresse.lower() == our_call
        ):
            self.process_ack_packet(packet)
        else:
            # Only ack messages that were sent directly to us
            if isinstance(packet, packets.MessagePacket):
                if to_call and to_call.lower() == our_call:
                    # It's a MessagePacket and it's for us!
                    stats.APRSDStats().msgs_rx_inc()
                    # let any threads do their thing, then ack
                    # send an ack last
                    ack_pkt = packets.AckPacket(
                        from_call=self.config["aprsd"]["callsign"],
                        to_call=from_call,
                        msgNo=msg_id,
                    )
                    LOG.warning(f"Send AckPacket {ack_pkt}")
                    ack_pkt.send()
                    LOG.warning("Send ACK called Continue on")
                    #ack = messaging.AckMessage(
                    #    self.config["aprsd"]["callsign"],
                    #    from_call,
                    #    msg_id=msg_id,
                    #)
                    #ack.send()

                    self.process_our_message_packet(packet)
                else:
                    # Packet wasn't meant for us!
                    self.process_other_packet(packet, for_us=False)
            else:
                self.process_other_packet(
                    packet, for_us=(to_call.lower() == our_call),
                )
        LOG.debug("Packet processing complete")
        return False

    @abc.abstractmethod
    def process_our_message_packet(self, *args, **kwargs):
        """Process a MessagePacket destined for us!"""

    def process_other_packet(self, packet, for_us=False):
        """Process an APRS Packet that isn't a message or ack"""
        if not for_us:
            LOG.info("Got a packet not meant for us.")
        else:
            LOG.info("Got a non AckPacket/MessagePacket")
        LOG.info(packet)


class APRSDPluginProcessPacketThread(APRSDProcessPacketThread):
    """Process the packet through the plugin manager.

    This is the main aprsd server plugin processing thread."""

    def process_our_message_packet(self, packet):
        """Send the packet through the plugins."""
        from_call = packet.from_call
        if packet.addresse:
            to_call = packet.addresse
        else:
            to_call = None
        # msg = packet.get("message_text", None)
        # packet.get("msgNo", "0")
        # packet.get("response", None)
        pm = plugin.PluginManager()
        try:
            results = pm.run(packet)
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
                            msg_pkt = packets.MessagePacket(
                                from_call=self.config["aprsd"]["callsign"],
                                to_call=from_call,
                                message_text=subreply,
                            )
                            msg_pkt.send()
                            #msg = messaging.TextMessage(
                            #    self.config["aprsd"]["callsign"],
                            #    from_call,
                            #    subreply,
                            #)
                            #msg.send()
                elif isinstance(reply, messaging.Message):
                    # We have a message based object.
                    LOG.debug(f"Sending '{reply}'")
                    # Convert this to the new packet
                    msg_pkt = packets.MessagePacket(
                        from_call=reply.fromcall,
                        to_call=reply.tocall,
                        message_text=reply._raw_message,
                    )
                    #reply.send()
                    msg_pkt.send()
                    replied = True
                else:
                    replied = True
                    # A plugin can return a null message flag which signals
                    # us that they processed the message correctly, but have
                    # nothing to reply with, so we avoid replying with a
                    # usage string
                    if reply is not messaging.NULL_MESSAGE:
                        LOG.debug(f"Sending '{reply}'")
                        msg_pkt = packets.MessagePacket(
                            from_call=self.config["aprsd"]["callsign"],
                            to_call=from_call,
                            message_text=reply,
                        )
                        LOG.warning("Calling msg_pkg.send()")
                        msg_pkt.send()
                        LOG.warning("Calling msg_pkg.send() --- DONE")

                        #msg = messaging.TextMessage(
                        #    self.config["aprsd"]["callsign"],
                        #    from_call,
                        #    reply,
                        #)
                        #msg.send()

            # If the message was for us and we didn't have a
            # response, then we send a usage statement.
            if to_call == self.config["aprsd"]["callsign"] and not replied:
                LOG.warning("Sending help!")
                msg_pkt = packets.MessagePacket(
                    from_call=self.config["aprsd"]["callsign"],
                    to_call=from_call,
                    message_text="Unknown command! Send 'help' message for help",
                )
                msg_pkt.send()
                #msg = messaging.TextMessage(
                #    self.config["aprsd"]["callsign"],
                #    from_call,
                #    "Unknown command! Send 'help' message for help",
                #)
                #msg.send()
        except Exception as ex:
            LOG.error("Plugin failed!!!")
            LOG.exception(ex)
            # Do we need to send a reply?
            if to_call == self.config["aprsd"]["callsign"]:
                reply = "A Plugin failed! try again?"
                msg_pkt = packets.MessagePacket(
                    from_call=self.config["aprsd"]["callsign"],
                    to_call=from_call,
                    message_text=reply,
                )
                msg_pkt.send()
                #msg = messaging.TextMessage(
                #    self.config["aprsd"]["callsign"],
                #    from_call,
                #    reply,
                #)
                #msg.send()

        LOG.debug("Completed process_our_message_packet")
