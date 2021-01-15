import abc
import logging
import queue
import threading
import time

from aprsd import client, messaging, plugin
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


class APRSDRXThread(APRSDThread):
    def __init__(self, msg_queues, config):
        super().__init__("RX_MSG")
        self.msg_queues = msg_queues
        self.config = config

    def stop(self):
        self.thread_stop = True
        client.get_client().stop()

    def callback(self, packet):
        try:
            packet = aprslib.parse(packet)
            print(packet)
        except (aprslib.ParseError, aprslib.UnknownFormat):
            pass

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
        return

    def process_mic_e_packet(self, packet):
        LOG.info("Mic-E Packet detected.  Currenlty unsupported.")
        messaging.log_packet(packet)
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
            LOG.info("Got message: {}".format(packet))

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


class APRSDTXThread(APRSDThread):
    def __init__(self, msg_queues, config):
        super().__init__("TX_MSG")
        self.msg_queues = msg_queues
        self.config = config

    def loop(self):
        try:
            msg = self.msg_queues["tx"].get(timeout=0.1)
            msg.send()
        except queue.Empty:
            pass
        # Continue to loop
        return True
