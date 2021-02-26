import abc
import datetime
import logging
import queue
import threading
import time
import tracemalloc

import aprslib

from aprsd import client, kissclient, messaging, packets, plugin, stats, utils


LOG = logging.getLogger("APRSD")

RX_THREAD = "RX"
EMAIL_THREAD = "Email"

rx_msg_queue = queue.Queue(maxsize=20)
msg_queues = {
    "rx": rx_msg_queue,
}


class APRSDThreadList:
    """Singleton class that keeps track of application wide threads."""

    _instance = None

    threads_list = []
    lock = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls.lock = threading.Lock()
            cls.threads_list = []
        return cls._instance

    def add(self, thread_obj):
        with self.lock:
            self.threads_list.append(thread_obj)

    def remove(self, thread_obj):
        with self.lock:
            self.threads_list.remove(thread_obj)

    def stop_all(self):
        """Iterate over all threads and call stop on them."""
        with self.lock:
            for th in self.threads_list:
                LOG.debug(f"Stopping Thread {th.name}")
                th.stop()

    def __len__(self):
        with self.lock:
            return len(self.threads_list)


class APRSDThread(threading.Thread, metaclass=abc.ABCMeta):
    def __init__(self, name):
        super().__init__(name=name)
        self.thread_stop = False
        APRSDThreadList().add(self)

    def stop(self):
        self.thread_stop = True

    @abc.abstractmethod
    def loop(self):
        pass

    def run(self):
        LOG.debug("Starting")
        while not self.thread_stop:
            can_loop = self.loop()
            if not can_loop:
                self.stop()
        APRSDThreadList().remove(self)
        LOG.debug("Exiting")


class KeepAliveThread(APRSDThread):
    cntr = 0
    checker_time = datetime.datetime.now()

    def __init__(self, config):
        tracemalloc.start()
        super().__init__("KeepAlive")
        self.config = config

    def loop(self):
        if self.cntr % 60 == 0:
            tracker = messaging.MsgTrack()
            stats_obj = stats.APRSDStats()
            pl = packets.PacketList()
            thread_list = APRSDThreadList()
            now = datetime.datetime.now()
            last_email = stats_obj.email_thread_time
            if last_email:
                email_thread_time = utils.strfdelta(now - last_email)
            else:
                email_thread_time = "N/A"

            last_msg_time = utils.strfdelta(now - stats_obj.aprsis_keepalive)

            current, peak = tracemalloc.get_traced_memory()
            stats_obj.set_memory(current)
            stats_obj.set_memory_peak(peak)
            keepalive = (
                "{} - Uptime {} RX:{} TX:{} Tracker:{} Msgs TX:{} RX:{} "
                "Last:{} Email: {} - RAM Current:{} Peak:{} Threads:{}"
            ).format(
                self.config["aprs"]["login"],
                utils.strfdelta(stats_obj.uptime),
                pl.total_recv,
                pl.total_tx,
                len(tracker),
                stats_obj.msgs_tx,
                stats_obj.msgs_rx,
                last_msg_time,
                email_thread_time,
                utils.human_size(current),
                utils.human_size(peak),
                len(thread_list),
            )
            LOG.info(keepalive)
            # Check version every hour
            delta = now - self.checker_time
            if delta > datetime.timedelta(hours=1):
                self.checker_time = now
                level, msg = utils._check_version()
                if level:
                    LOG.warning(msg)
        self.cntr += 1
        time.sleep(1)
        return True


class APRSDRXThread(APRSDThread):
    def __init__(self, msg_queues, config):
        super().__init__("RX_MSG")
        self.msg_queues = msg_queues
        self.config = config

    def stop(self):
        self.thread_stop = True
        client.get_client().stop()

    def loop(self):
        aprs_client = client.get_client()

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
            aprs_client.consumer(self.process_packet, raw=False, blocking=False)

        except aprslib.exceptions.ConnectionDrop:
            LOG.error("Connection dropped, reconnecting")
            time.sleep(5)
            # Force the deletion of the client object connected to aprs
            # This will cause a reconnect, next time client.get_client()
            # is called
            client.Client().reset()
        # Continue to loop
        return True

    def process_packet(self, packet):
        thread = APRSDProcessPacketThread(packet=packet, config=self.config)
        thread.start()


class APRSDProcessPacketThread(APRSDThread):

    def __init__(self, packet, config):
        self.packet = packet
        self.config = config
        name = self.packet["raw"][:10]
        super().__init__(f"RX_PACKET-{name}")

    def process_ack_packet(self, packet):
        ack_num = packet.get("msgNo")
        LOG.info(f"Got ack for message {ack_num}")
        messaging.log_message(
            "ACK",
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
        """Process a packet recieved from aprs-is server."""
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
        if tocall == self.config["aprs"]["login"] and msg_response == "ack":
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
            if tocall == self.config["aprs"]["login"]:
                stats.APRSDStats().msgs_rx_inc()
                # let any threads do their thing, then ack
                # send an ack last
                ack = messaging.AckMessage(
                    self.config["aprs"]["login"],
                    fromcall,
                    msg_id=msg_id,
                )
                ack.send()

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

                            msg = messaging.TextMessage(
                                self.config["aprs"]["login"],
                                fromcall,
                                subreply,
                            )
                            msg.send()

                    else:
                        replied = True
                        # A plugin can return a null message flag which signals
                        # us that they processed the message correctly, but have
                        # nothing to reply with, so we avoid replying with a
                        # usage string
                        if reply is not messaging.NULL_MESSAGE:
                            LOG.debug(f"Sending '{reply}'")

                            msg = messaging.TextMessage(
                                self.config["aprs"]["login"],
                                fromcall,
                                reply,
                            )
                            msg.send()

                # If the message was for us and we didn't have a
                # response, then we send a usage statement.
                if tocall == self.config["aprs"]["login"] and not replied:
                    reply = "Usage: weather, locate [call], time, fortune, ping"

                    msg = messaging.TextMessage(
                        self.config["aprs"]["login"],
                        fromcall,
                        reply,
                    )
                    msg.send()
            except Exception as ex:
                LOG.exception("Plugin failed!!!", ex)
                # Do we need to send a reply?
                if tocall == self.config["aprs"]["login"]:
                    reply = "A Plugin failed! try again?"
                    msg = messaging.TextMessage(
                        self.config["aprs"]["login"],
                        fromcall,
                        reply,
                    )
                    msg.send()

        LOG.debug("Packet processing complete")


class APRSDTXThread(APRSDThread):
    def __init__(self, msg_queues, config):
        super().__init__("TX_MSG")
        self.msg_queues = msg_queues
        self.config = config

    def loop(self):
        try:
            msg = self.msg_queues["tx"].get(timeout=1)
            msg.send()
        except queue.Empty:
            pass
        # Continue to loop
        return True


class KISSRXThread(APRSDThread):
    """Thread that connects to direwolf's TCPKISS interface.

    All Packets are processed and sent back out the direwolf
    interface instead of the aprs-is server.

    """

    def __init__(self, msg_queues, config):
        super().__init__("KISSRX_MSG")
        self.msg_queues = msg_queues
        self.config = config

    def stop(self):
        self.thread_stop = True
        kissclient.get_client().stop()

    def loop(self):
        kiss_client = kissclient.get_client()

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
            kiss_client.consumer(self.process_packet, callsign="APN382")
            kiss_client.loop.run_forever()

        except aprslib.exceptions.ConnectionDrop:
            LOG.error("Connection dropped, reconnecting")
            time.sleep(5)
            # Force the deletion of the client object connected to aprs
            # This will cause a reconnect, next time client.get_client()
            # is called
            client.Client().reset()
        # Continue to loop

    @trace.trace
    def process_packet(self, interface, frame, match):
        """Process a packet recieved from aprs-is server."""

        LOG.debug("Got an APRS Frame '{}'".format(frame))

        payload = str(frame.payload.decode())
        msg = "{}:{}".format(str(frame.header), payload)

        packet = aprslib.parse(msg)
        LOG.debug(packet)

        try:
            stats.APRSDStats().msgs_rx_inc()

            msg = packet.get("message_text", None)
            msg_format = packet.get("format", None)
            msg_response = packet.get("response", None)
            if msg_format == "message" and msg:
                # we want to send the message through the
                # plugins
                self.process_message_packet(packet)
                return
            elif msg_response == "ack":
                self.process_ack_packet(packet)
                return

            if msg_format == "mic-e":
                # process a mic-e packet
                self.process_mic_e_packet(packet)
                return

        except (aprslib.ParseError, aprslib.UnknownFormat) as exp:
            LOG.exception("Failed to parse packet from aprs-is", exp)

    @trace.trace
    def process_message_packet(self, packet):
        LOG.debug("Message packet rx")
        fromcall = packet["from"]
        message = packet.get("message_text", None)
        msg_id = packet.get("msgNo", "0")
        messaging.log_message(
            "Received Message",
            packet["raw"],
            message,
            fromcall=fromcall,
            msg_num=msg_id,
        )
        found_command = False
        # Get singleton of the PM
        pm = plugin.PluginManager()
        try:
            results = pm.run(fromcall=fromcall, message=message, ack=msg_id)
            for reply in results:
                found_command = True
                # A plugin can return a null message flag which signals
                # us that they processed the message correctly, but have
                # nothing to reply with, so we avoid replying with a usage string
                if reply is not messaging.NULL_MESSAGE:
                    LOG.debug("Sending '{}'".format(reply))

                    msg = messaging.TextMessage(
                        self.config["aprs"]["login"],
                        fromcall,
                        reply,
                        transport=messaging.MESSAGE_TRANSPORT_TCPKISS,
                    )
                    self.msg_queues["tx"].put(msg)
                else:
                    LOG.debug("Got NULL MESSAGE from plugin")

            if not found_command:
                plugins = pm.get_plugins()
                names = [x.command_name for x in plugins]
                names.sort()

                # reply = "Usage: {}".format(", ".join(names))
                reply = "Usage: weather, locate [call], time, fortune, ping"

                msg = messaging.TextMessage(
                    self.config["aprs"]["login"],
                    fromcall,
                    reply,
                    transport=messaging.MESSAGE_TRANSPORT_TCPKISS,
                )
                self.msg_queues["tx"].put(msg)
        except Exception as ex:
            LOG.exception("Plugin failed!!!", ex)
            reply = "A Plugin failed! try again?"
            msg = messaging.TextMessage(
                self.config["aprs"]["login"],
                fromcall,
                reply,
                transport=messaging.MESSAGE_TRANSPORT_TCPKISS,
            )
            self.msg_queues["tx"].put(msg)

        # let any threads do their thing, then ack
        # send an ack last
        ack = messaging.AckMessage(
            self.config["aprs"]["login"],
            fromcall,
            msg_id=msg_id,
            transport=messaging.MESSAGE_TRANSPORT_TCPKISS,
        )
        self.msg_queues["tx"].put(ack)
        LOG.debug("Packet processing complete")

    def process_ack_packet(self, packet):
        ack_num = packet.get("msgNo")
        LOG.info("Got ack for message {}".format(ack_num))
        messaging.log_message(
            "ACK",
            packet["raw"],
            None,
            ack=ack_num,
            fromcall=packet["from"],
        )
        tracker = messaging.MsgTrack()
        tracker.remove(ack_num)
        stats.APRSDStats().ack_rx_inc()
        return

    def process_mic_e_packet(self, packet):
        LOG.info("Mic-E Packet detected.  Currenlty unsupported.")
        messaging.log_packet(packet)
        stats.APRSDStats().msgs_mice_inc()
        return
