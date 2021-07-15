import abc
import datetime
import logging
import queue
import threading
import time
import tracemalloc

from aprsd import client, messaging, packets, plugin, stats, utils
import aprslib

LOG = logging.getLogger("APRSD")

RX_THREAD = "RX"
TX_THREAD = "TX"
EMAIL_THREAD = "Email"


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
                th.stop()


class APRSDThread(threading.Thread, metaclass=abc.ABCMeta):
    def __init__(self, name):
        super().__init__(name=name)
        self.thread_stop = False
        APRSDThreadList().add(self)

    def stop(self):
        self.thread_stop = True

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

    def __init__(self):
        tracemalloc.start()
        super().__init__("KeepAlive")

    def loop(self):
        if self.cntr % 6 == 0:
            tracker = messaging.MsgTrack()
            stats_obj = stats.APRSDStats()
            packets_list = packets.PacketList().packet_list
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
            keepalive = "Uptime {} Tracker {} " "Msgs TX:{} RX:{} Last:{} Email:{} Packets:{} RAM Current:{} Peak:{}".format(
                utils.strfdelta(stats_obj.uptime),
                len(tracker),
                stats_obj.msgs_tx,
                stats_obj.msgs_rx,
                last_msg_time,
                email_thread_time,
                len(packets_list),
                utils.human_size(current),
                utils.human_size(peak),
            )
            LOG.debug(keepalive)
            # Check version every hour
            delta = now - self.checker_time
            if delta > datetime.timedelta(hours=1):
                self.checker_time = now
                level, msg = utils._check_version()
                if level:
                    LOG.warning(msg)
        self.cntr += 1
        time.sleep(10)
        return True


class APRSDNotifyThread(APRSDThread):
    last_seen = {}

    def __init__(self, msg_queues, config):
        super().__init__("NOTIFY_MSG")
        self.msg_queues = msg_queues
        self.config = config
        for callsign in config["aprsd"]["watch_list"].get("callsigns", []):
            call = callsign.replace("*", "")
            # FIXME(waboring) - we should fetch the last time we saw
            # a beacon from a callsign or some other mechanism to find
            # last time a message was seen by aprs-is.  For now this
            # is all we can do.
            self.last_seen[call] = datetime.datetime.now()
        self.update_stats()

    def update_stats(self):
        stats_seen = {}
        for callsign in self.last_seen:
            stats_seen[callsign] = str(self.last_seen[callsign])

        stats.APRSDStats().update_watch_list(stats_seen)

    def loop(self):
        try:
            packet = self.msg_queues["notify"].get(timeout=5)

            if packet["from"] in self.last_seen:
                # We only notify if the last time a callsign was seen
                # is older than the alert_time_seconds
                now = datetime.datetime.now()
                age = str(now - self.last_seen[packet["from"]])

                delta = utils.parse_delta_str(age)
                d = datetime.timedelta(**delta)

                watch_list_conf = self.config["aprsd"]["watch_list"]
                max_timeout = {
                    "seconds": watch_list_conf["alert_time_seconds"],
                }
                max_delta = datetime.timedelta(**max_timeout)

                if d > max_delta:
                    LOG.info(
                        "NOTIFY {} last seen {} max age={}".format(
                            packet["from"],
                            age,
                            max_delta,
                        ),
                    )
                    # NOW WE RUN through the notify plugins.
                    # If they return a msg, then we queue it for sending.
                    pm = plugin.PluginManager()
                    results = pm.notify(packet)
                    for reply in results:
                        if reply is not messaging.NULL_MESSAGE:
                            LOG.debug("Sending '{}'".format(reply))

                            msg = messaging.TextMessage(
                                self.config["aprs"]["login"],
                                watch_list_conf["alert_callsign"],
                                reply,
                            )
                            self.msg_queues["tx"].put(msg)
                        else:
                            LOG.debug("Got NULL MESSAGE from plugin")

                else:
                    LOG.debug(
                        "Not old enough to notify callsign {}: {} < {}".format(
                            packet["from"],
                            age,
                            max_delta,
                        ),
                    )

                LOG.debug("Update last seen from {}".format(packet["from"]))
                self.last_seen[packet["from"]] = now
            else:
                LOG.debug("Ignoring packet from {}".format(packet["from"]))

            # Allows stats object to have latest info from the last_seen dict
            self.update_stats()
            LOG.debug("Packet processing complete")
        except queue.Empty:
            pass
        # Continue to loop
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

        # if we have a watch list enabled, we need to add filtering
        # to enable seeing packets from the watch list.
        if "watch_list" in self.config["aprsd"] and self.config["aprsd"][
            "watch_list"
        ].get("enabled", False):
            # watch list is enabled
            watch_list = self.config["aprsd"]["watch_list"].get(
                "callsigns",
                [],
            )
            # make sure the timeout is set or this doesn't work
            if watch_list:
                filter_str = "p/{}".format("/".join(watch_list))
                aprs_client.set_filter(filter_str)
            else:
                LOG.warning("Watch list enabled, but no callsigns set.")

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

    def process_message_packet(self, packet):
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
            results = pm.run(packet)
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
                    )
                    self.msg_queues["tx"].put(msg)
                else:
                    LOG.debug("Got NULL MESSAGE from plugin")

            if not found_command:
                plugins = pm.get_msg_plugins()
                names = [x.command_name for x in plugins]
                names.sort()

                # reply = "Usage: {}".format(", ".join(names))
                reply = "Usage: weather, locate [call], time, fortune, ping"

                msg = messaging.TextMessage(
                    self.config["aprs"]["login"],
                    fromcall,
                    reply,
                )
                self.msg_queues["tx"].put(msg)
        except Exception as ex:
            LOG.exception("Plugin failed!!!", ex)
            reply = "A Plugin failed! try again?"
            msg = messaging.TextMessage(self.config["aprs"]["login"], fromcall, reply)
            self.msg_queues["tx"].put(msg)

        # let any threads do their thing, then ack
        # send an ack last
        ack = messaging.AckMessage(
            self.config["aprs"]["login"],
            fromcall,
            msg_id=msg_id,
        )
        self.msg_queues["tx"].put(ack)
        LOG.debug("Packet processing complete")

    def process_packet(self, packet):
        """Process a packet recieved from aprs-is server."""

        try:
            LOG.debug("Adding packet to notify queue {}".format(packet["raw"]))
            self.msg_queues["notify"].put(packet)

            # since we can see packets from anyone now with the
            # watch list, we need to filter messages directly only to us.
            tocall = packet.get("addresse", None)
            if tocall == self.config["aprs"]["login"]:
                stats.APRSDStats().msgs_rx_inc()
                packets.PacketList().add(packet)

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
            else:
                LOG.debug(
                    "Packet wasn't meant for us '{}'. Ignoring packet to '{}'".format(
                        self.config["aprs"]["login"],
                        tocall,
                    ),
                )

        except (aprslib.ParseError, aprslib.UnknownFormat) as exp:
            LOG.exception("Failed to parse packet from aprs-is", exp)


class APRSDTXThread(APRSDThread):
    def __init__(self, msg_queues, config):
        super().__init__("TX_MSG")
        self.msg_queues = msg_queues
        self.config = config

    def loop(self):
        try:
            msg = self.msg_queues["tx"].get(timeout=5)
            packets.PacketList().add(msg.dict())
            msg.send()
        except queue.Empty:
            pass
        # Continue to loop
        return True
