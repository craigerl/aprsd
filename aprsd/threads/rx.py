import abc
import logging
import queue
import time

import aprslib
from oslo_config import cfg

from aprsd import client, packets, plugin
from aprsd.threads import APRSDThread, tx


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class APRSDRXThread(APRSDThread):
    def __init__(self, packet_queue):
        super().__init__("RX_MSG")
        self.packet_queue = packet_queue
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


class APRSDDupeRXThread(APRSDRXThread):
    """Process received packets.

    This is the main APRSD Server command thread that
    receives packets and makes sure the packet
    hasn't been seen previously before sending it on
    to be processed.
    """

    def process_packet(self, *args, **kwargs):
        """This handles the processing of an inbound packet.

        When a packet is received by the connected client object,
        it sends the raw packet into this function.  This function then
        decodes the packet via the client, and then processes the packet.
        Ack Packets are sent to the PluginProcessPacketThread for processing.
        All other packets have to be checked as a dupe, and then only after
        we haven't seen this packet before, do we send it to the
        PluginProcessPacketThread for processing.
        """
        packet = self._client.decode_packet(*args, **kwargs)
        # LOG.debug(raw)
        packet.log(header="RX")

        if isinstance(packet, packets.AckPacket):
            # We don't need to drop AckPackets, those should be
            # processed.
            self.packet_queue.put(packet)
        else:
            # Make sure we aren't re-processing the same packet
            # For RF based APRS Clients we can get duplicate packets
            # So we need to track them and not process the dupes.
            found = False
            pkt_list = packets.PacketList()
            try:
                # Find the packet in the list of already seen packets
                # Based on the packet.key
                found = pkt_list.find(packet)
            except KeyError:
                found = False

            if not found:
                # If we are in the process of already ack'ing
                # a packet, we should drop the packet
                # because it's a dupe within the time that
                # we send the 3 acks for the packet.
                pkt_list.rx(packet)
                self.packet_queue.put(packet)
            elif packet.timestamp - found.timestamp < CONF.packet_dupe_timeout:
                # If the packet came in within 60 seconds of the
                # Last time seeing the packet, then we drop it as a dupe.
                LOG.warning(f"Packet {packet.from_call}:{packet.msgNo} already tracked, dropping.")
            else:
                LOG.warning(
                    f"Packet {packet.from_call}:{packet.msgNo} already tracked "
                    f"but older than {CONF.packet_dupe_timeout} seconds. processing.",
                )
                pkt_list.rx(packet)
                self.packet_queue.put(packet)


class APRSDPluginRXThread(APRSDDupeRXThread):
    """"Process received packets.

    For backwards compatibility, we keep the APRSDPluginRXThread.
    """


class APRSDProcessPacketThread(APRSDThread):
    """Base class for processing received packets.

    This is the base class for processing packets coming from
    the consumer.  This base class handles sending ack packets and
    will ack a message before sending the packet to the subclass
    for processing."""

    def __init__(self, packet_queue):
        self.packet_queue = packet_queue
        super().__init__("ProcessPKT")
        self._loop_cnt = 1

    def process_ack_packet(self, packet):
        """We got an ack for a message, no need to resend it."""
        ack_num = packet.msgNo
        LOG.info(f"Got ack for message {ack_num}")
        pkt_tracker = packets.PacketTrack()
        pkt_tracker.remove(ack_num)

    def process_reject_packet(self, packet):
        """We got a reject message for a packet.  Stop sending the message."""
        ack_num = packet.msgNo
        LOG.info(f"Got REJECT for message {ack_num}")
        pkt_tracker = packets.PacketTrack()
        pkt_tracker.remove(ack_num)

    def loop(self):
        try:
            packet = self.packet_queue.get(timeout=1)
            if packet:
                self.process_packet(packet)
        except queue.Empty:
            pass
        self._loop_cnt += 1
        return True

    def process_packet(self, packet):
        """Process a packet received from aprs-is server."""
        LOG.debug(f"ProcessPKT-LOOP {self._loop_cnt}")
        our_call = CONF.callsign.lower()

        from_call = packet.from_call
        if packet.addresse:
            to_call = packet.addresse
        else:
            to_call = packet.to_call
        msg_id = packet.msgNo

        # We don't put ack packets destined for us through the
        # plugins.
        if (
            isinstance(packet, packets.AckPacket)
            and packet.addresse.lower() == our_call
        ):
            self.process_ack_packet(packet)
        elif (
            isinstance(packet, packets.RejectPacket)
            and packet.addresse.lower() == our_call
        ):
            self.process_reject_packet(packet)
        else:
            # Only ack messages that were sent directly to us
            if isinstance(packet, packets.MessagePacket):
                if to_call and to_call.lower() == our_call:
                    # It's a MessagePacket and it's for us!
                    # let any threads do their thing, then ack
                    # send an ack last
                    tx.send(
                        packets.AckPacket(
                            from_call=CONF.callsign,
                            to_call=from_call,
                            msgNo=msg_id,
                        ),
                    )

                    self.process_our_message_packet(packet)
                else:
                    # Packet wasn't meant for us!
                    self.process_other_packet(packet, for_us=False)
            else:
                self.process_other_packet(
                    packet, for_us=(to_call.lower() == our_call),
                )
        LOG.debug(f"Packet processing complete for pkt '{packet.key}'")
        return False

    @abc.abstractmethod
    def process_our_message_packet(self, packet):
        """Process a MessagePacket destined for us!"""

    def process_other_packet(self, packet, for_us=False):
        """Process an APRS Packet that isn't a message or ack"""
        if not for_us:
            LOG.info("Got a packet not meant for us.")
        else:
            LOG.info("Got a non AckPacket/MessagePacket")


class APRSDPluginProcessPacketThread(APRSDProcessPacketThread):
    """Process the packet through the plugin manager.

    This is the main aprsd server plugin processing thread."""

    def process_other_packet(self, packet, for_us=False):
        pm = plugin.PluginManager()
        try:
            results = pm.run_watchlist(packet)
            for reply in results:
                if isinstance(reply, list):
                    for subreply in reply:
                        LOG.debug(f"Sending '{subreply}'")
                        if isinstance(subreply, packets.Packet):
                            tx.send(subreply)
                        else:
                            wl = CONF.watch_list
                            to_call = wl["alert_callsign"]
                            tx.send(
                                packets.MessagePacket(
                                    from_call=CONF.callsign,
                                    to_call=to_call,
                                    message_text=subreply,
                                ),
                            )
                elif isinstance(reply, packets.Packet):
                    # We have a message based object.
                    tx.send(reply)
        except Exception as ex:
            LOG.error("Plugin failed!!!")
            LOG.exception(ex)

    def process_our_message_packet(self, packet):
        """Send the packet through the plugins."""
        from_call = packet.from_call
        if packet.addresse:
            to_call = packet.addresse
        else:
            to_call = None

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
                        if isinstance(subreply, packets.Packet):
                            tx.send(subreply)
                        else:
                            tx.send(
                                packets.MessagePacket(
                                    from_call=CONF.callsign,
                                    to_call=from_call,
                                    message_text=subreply,
                                ),
                            )
                elif isinstance(reply, packets.Packet):
                    # We have a message based object.
                    tx.send(reply)
                    replied = True
                else:
                    replied = True
                    # A plugin can return a null message flag which signals
                    # us that they processed the message correctly, but have
                    # nothing to reply with, so we avoid replying with a
                    # usage string
                    if reply is not packets.NULL_MESSAGE:
                        LOG.debug(f"Sending '{reply}'")
                        tx.send(
                            packets.MessagePacket(
                                from_call=CONF.callsign,
                                to_call=from_call,
                                message_text=reply,
                            ),
                        )

            # If the message was for us and we didn't have a
            # response, then we send a usage statement.
            if to_call == CONF.callsign and not replied:
                LOG.warning("Sending help!")
                message_text = "Unknown command! Send 'help' message for help"
                tx.send(
                    packets.MessagePacket(
                        from_call=CONF.callsign,
                        to_call=from_call,
                        message_text=message_text,
                    ),
                )
        except Exception as ex:
            LOG.error("Plugin failed!!!")
            LOG.exception(ex)
            # Do we need to send a reply?
            if to_call == CONF.callsign:
                reply = "A Plugin failed! try again?"
                tx.send(
                    packets.MessagePacket(
                        from_call=CONF.callsign,
                        to_call=from_call,
                        message_text=reply,
                    ),
                )

        LOG.debug("Completed process_our_message_packet")
