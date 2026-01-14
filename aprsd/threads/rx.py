import abc
import logging
import queue
import time

import aprslib
from oslo_config import cfg

from aprsd import packets, plugin
from aprsd.client.client import APRSDClient
from aprsd.packets import collector, core, filter
from aprsd.packets import log as packet_log
from aprsd.threads import APRSDThread, tx

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class APRSDRXThread(APRSDThread):
    """
    Thread to receive packets from the APRS Client and put them on the packet queue.

    Args:
        packet_queue: The queue to put the packets in.
    """

    _client = None

    # This is the queue that packets are sent to for processing.
    # We process packets in a separate thread to help prevent
    # getting blocked by the APRS server trying to send us packets.
    packet_queue = None

    pkt_count = 0

    def __init__(self, packet_queue: queue.Queue):
        """Initialize the APRSDRXThread.

        Args:
            packet_queue: The queue to put the packets in.
        """
        super().__init__('RX_PKT')
        self.packet_queue = packet_queue

    def stop(self):
        self.thread_stop = True
        if self._client:
            self._client.close()

    def loop(self):
        if not self._client:
            self._client = APRSDClient()
            time.sleep(1)
            return True

        if not self._client.is_alive:
            self._client = APRSDClient()
            time.sleep(1)
            return True

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
            self._client.consumer(
                self.process_packet,
                raw=True,
            )
        except (
            aprslib.exceptions.ConnectionDrop,
            aprslib.exceptions.ConnectionError,
        ):
            LOG.error('Connection dropped, reconnecting')
            # Force the deletion of the client object connected to aprs
            # This will cause a reconnect, next time client.get_client()
            # is called
            self._client.reset()
            time.sleep(5)
        except Exception as ex:
            LOG.exception(ex)
            LOG.error('Resetting connection and trying again.')
            self._client.reset()
            time.sleep(5)
        return True

    def process_packet(self, *args, **kwargs):
        """Put the raw packet on the queue.

        The processing of the packet will happen in a separate thread.
        """
        if not args:
            LOG.warning('No frame received to process?!?!')
            return
        self.pkt_count += 1
        self.packet_queue.put(args[0])


class APRSDFilterThread(APRSDThread):
    """
    Thread to filter packets on the packet queue.
    Args:
        thread_name: The name of the thread.
        packet_queue: The queue to get the packets from.
    """

    def __init__(self, thread_name: str, packet_queue: queue.Queue):
        """Initialize the APRSDFilterThread.

        Args:
            thread_name: The name of the thread.
            packet_queue: The queue to get the packets from.
        """
        super().__init__(thread_name)
        self.packet_queue = packet_queue
        self.packet_count = 0
        self._client = APRSDClient()

    def filter_packet(self, packet: type[core.Packet]) -> type[core.Packet] | None:
        # Do any packet filtering prior to processing
        if not filter.PacketFilter().filter(packet):
            return None
        return packet

    def print_packet(self, packet):
        """Allow a child of this class to override this.

        This is helpful if for whatever reason the child class
        doesn't want to log packets.

        """
        packet_log.log(packet, packet_count=self.packet_count)

    def loop(self):
        try:
            pkt = self.packet_queue.get(timeout=1)
            self.packet_count += 1
            # We use the client here, because the specific
            # driver may need to decode the packet differently.
            packet = self._client.decode_packet(pkt)
            if not packet:
                # We mark this as debug, since there are so many
                # packets that are on the APRS network, and we don't
                # want to spam the logs with this.
                LOG.debug(f'Packet failed to parse. "{pkt}"')
                return True
            self.print_packet(packet)
            if packet:
                if self.filter_packet(packet):
                    # The packet has passed all filters, so we collect it.
                    # and process it.
                    collector.PacketCollector().rx(packet)
                    self.process_packet(packet)
        except queue.Empty:
            pass
        return True


class APRSDProcessPacketThread(APRSDFilterThread):
    """Base class for processing received packets after they have been filtered.

    Packets are received from the client, then filtered for dupes,
    then sent to the packet queue.  This thread pulls packets from
    the packet queue for processing.

    This is the base class for processing packets coming from
    the consumer.  This base class handles sending ack packets and
    will ack a message before sending the packet to the subclass
    for processing."""

    def __init__(self, packet_queue: queue.Queue):
        super().__init__('ProcessPKT', packet_queue=packet_queue)
        if not CONF.enable_sending_ack_packets:
            LOG.warning(
                'Sending ack packets is disabled, messages will not be acknowledged.',
            )

    def process_ack_packet(self, packet):
        """We got an ack for a message, no need to resend it."""
        ack_num = packet.msgNo
        LOG.debug(f'Got ack for message {ack_num}')
        collector.PacketCollector().rx(packet)

    def process_piggyback_ack(self, packet):
        """We got an ack embedded in a packet."""
        ack_num = packet.ackMsgNo
        LOG.debug(f'Got PiggyBackAck for message {ack_num}')
        collector.PacketCollector().rx(packet)

    def process_reject_packet(self, packet):
        """We got a reject message for a packet.  Stop sending the message."""
        ack_num = packet.msgNo
        LOG.debug(f'Got REJECT for message {ack_num}')
        collector.PacketCollector().rx(packet)

    def process_packet(self, packet):
        """Process a packet received from aprs-is server."""
        LOG.debug(f'ProcessPKT-LOOP {self.loop_count}')

        # set this now as we are going to process it.
        # This is used during dupe checking, so set it early
        packet.processed = True

        our_call = CONF.callsign.lower()

        from_call = packet.from_call
        if hasattr(packet, 'addresse') and packet.addresse:
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
            if hasattr(packet, 'ackMsgNo') and packet.ackMsgNo:
                # we got an ack embedded in this packet
                # we need to handle the ack
                self.process_piggyback_ack(packet)
            # Only ack messages that were sent directly to us
            if isinstance(packet, packets.MessagePacket):
                if to_call and to_call.lower() == our_call:
                    # It's a MessagePacket and it's for us!
                    # let any threads do their thing, then ack
                    # send an ack last
                    if msg_id:
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
                    packet,
                    for_us=(to_call.lower() == our_call),
                )
        LOG.debug(f"Packet processing complete for pkt '{packet.key}'")
        return False

    @abc.abstractmethod
    def process_our_message_packet(self, packet):
        """Process a MessagePacket destined for us!"""

    def process_other_packet(self, packet, for_us=False):
        """Process an APRS Packet that isn't a message or ack"""
        if not for_us:
            LOG.info(f"Got a packet meant for someone else '{packet.to_call}'")
        else:
            LOG.info('Got a non AckPacket/MessagePacket')


class APRSDPluginProcessPacketThread(APRSDProcessPacketThread):
    """Process the packet through the plugin manager.

    This is the main aprsd server plugin processing thread.
    Args:
        packet_queue: The queue to get the packets from.
    """

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
                            to_call = wl['alert_callsign']
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
            LOG.error('Plugin failed!!!')
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
                # Tailor the messages accordingly
                if CONF.load_help_plugin:
                    LOG.warning('Sending help!')
                    message_text = "Unknown command! Send 'help' message for help"
                else:
                    LOG.warning('Unknown command!')
                    message_text = 'Unknown command!'

                tx.send(
                    packets.MessagePacket(
                        from_call=CONF.callsign,
                        to_call=from_call,
                        message_text=message_text,
                    ),
                )
        except Exception as ex:
            LOG.error('Plugin failed!!!')
            LOG.exception(ex)
            # Do we need to send a reply?
            if to_call == CONF.callsign:
                reply = 'A Plugin failed! try again?'
                tx.send(
                    packets.MessagePacket(
                        from_call=CONF.callsign,
                        to_call=from_call,
                        message_text=reply,
                    ),
                )

        LOG.debug('Completed process_our_message_packet')
