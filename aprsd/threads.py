import abc
import datetime
import logging
import queue
import threading
import time
import tracemalloc

import aprslib

from aprsd import client, messaging, packets, plugin, stats, utils


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
        max_timeout = {"hours": 0.0, "minutes": 5, "seconds": 0}
        self.max_delta = datetime.timedelta(**max_timeout)

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

            # See if we should reset the aprs-is client
            # Due to losing a keepalive from them
            delta_dict = utils.parse_delta_str(last_msg_time)
            delta = datetime.timedelta(**delta_dict)

            if delta > self.max_delta:
                #  We haven't gotten a keepalive from aprs-is in a while
                # reset the connection.a
                if not client.KISSClient.is_enabled(self.config):
                    LOG.warning("Resetting connection to APRS-IS.")
                    client.factory.create().reset()

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

        except aprslib.exceptions.ConnectionDrop:
            LOG.error("Connection dropped, reconnecting")
            time.sleep(5)
            # Force the deletion of the client object connected to aprs
            # This will cause a reconnect, next time client.get_client()
            # is called
            self._client.reset()
        # Continue to loop
        return True

    def process_packet(self, *args, **kwargs):
        packet = self._client.decode_packet(*args, **kwargs)
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
                            if isinstance(subreply, messaging.Message):
                                subreply.send()
                            else:
                                msg = messaging.TextMessage(
                                    self.config["aprs"]["login"],
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
                                self.config["aprs"]["login"],
                                fromcall,
                                reply,
                            )
                            msg.send()

                # If the message was for us and we didn't have a
                # response, then we send a usage statement.
                if tocall == self.config["aprs"]["login"] and not replied:
                    LOG.warning("Sending help!")
                    msg = messaging.TextMessage(
                        self.config["aprs"]["login"],
                        fromcall,
                        "Unknown command! Send 'help' message for help",
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
