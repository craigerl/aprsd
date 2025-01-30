import abc
import logging
import queue
import time

import aprslib
from oslo_config import cfg

from aprsd import packets, plugin
from aprsd.client import client_factory
from aprsd.packets import collector, filter
from aprsd.packets import log as packet_log
from aprsd.threads import APRSDThread, tx

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class APRSDRXThread(APRSDThread):
    """Main Class to connect to an APRS Client and recieve packets.

    A packet is received in the main loop and then sent to the
    process_packet method, which sends the packet through the collector
    to track the packet for stats, and then put into the packet queue
    for processing in a separate thread.
    """

    _client = None

    # This is the queue that packets are sent to for processing.
    # We process packets in a separate thread to help prevent
    # getting blocked by the APRS server trying to send us packets.
    packet_queue = None

    def __init__(self, packet_queue):
        super().__init__('RX_PKT')
        self.packet_queue = packet_queue

    def stop(self):
        self.thread_stop = True
        if self._client:
            self._client.stop()

    def loop(self):
        if not self._client:
            self._client = client_factory.create()
            time.sleep(1)
            return True

        if not self._client.is_connected:
            self._client = client_factory.create()
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
                raw=False,
                blocking=False,
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
        except Exception:
            # LOG.exception(ex)
            LOG.error('Resetting connection and trying again.')
            self._client.reset()
            time.sleep(5)
        return True

    def process_packet(self, *args, **kwargs):
        packet = self._client.decode_packet(*args, **kwargs)
        if not packet:
            LOG.error(
                'No packet received from decode_packet.  Most likely a failure to parse'
            )
            return
        packet_log.log(packet)
        pkt_list = packets.PacketList()

        if isinstance(packet, packets.AckPacket):
            # We don't need to drop AckPackets, those should be
            # processed.
            self.packet_queue.put(packet)
        else:
            # Make sure we aren't re-processing the same packet
            # For RF based APRS Clients we can get duplicate packets
            # So we need to track them and not process the dupes.
            found = False
            try:
                # Find the packet in the list of already seen packets
                # Based on the packet.key
                found = pkt_list.find(packet)
                if not packet.msgNo:
                    # If the packet doesn't have a message id
                    # then there is no reliable way to detect
                    # if it's a dupe, so we just pass it on.
                    # it shouldn't get acked either.
                    found = False
            except KeyError:
                found = False

            if not found:
                # We haven't seen this packet before, so we process it.
                collector.PacketCollector().rx(packet)
                self.packet_queue.put(packet)
            elif packet.timestamp - found.timestamp < CONF.packet_dupe_timeout:
                # If the packet came in within N seconds of the
                # Last time seeing the packet, then we drop it as a dupe.
                LOG.warning(
                    f'Packet {packet.from_call}:{packet.msgNo} already tracked, dropping.'
                )
            else:
                LOG.warning(
                    f'Packet {packet.from_call}:{packet.msgNo} already tracked '
                    f'but older than {CONF.packet_dupe_timeout} seconds. processing.',
                )
                collector.PacketCollector().rx(packet)
                self.packet_queue.put(packet)


class APRSDFilterThread(APRSDThread):
    def __init__(self, thread_name, packet_queue):
        super().__init__(thread_name)
        self.packet_queue = packet_queue

    def filter_packet(self, packet):
        # Do any packet filtering prior to processing
        if not filter.PacketFilter().filter(packet):
            return None
        return packet

    def print_packet(self, packet):
        """Allow a child of this class to override this.

        This is helpful if for whatever reason the child class
        doesn't want to log packets.

        """
        packet_log.log(packet)

    def loop(self):
        try:
            packet = self.packet_queue.get(timeout=1)
            self.print_packet(packet)
            if packet:
                if self.filter_packet(packet):
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

    def __init__(self, packet_queue):
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
            LOG.info("Got a packet meant for someone else '{packet.to_call}'")
        else:
            LOG.info('Got a non AckPacket/MessagePacket')


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
