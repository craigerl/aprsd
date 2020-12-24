import logging
import queue
import threading
import time

import aprslib

from aprsd import client, messaging, plugin

LOG = logging.getLogger("APRSD")


class APRSDThread(threading.Thread):
    def __init__(self, name, msg_queues, config):
        super(APRSDThread, self).__init__(name=name)
        self.msg_queues = msg_queues
        self.config = config
        self.thread_stop = False

    def stop(self):
        self.thread_stop = True

    def run(self):
        while not self.thread_stop:
            self._run()


class APRSDRXThread(APRSDThread):
    def __init__(self, msg_queues, config):
        super(APRSDRXThread, self).__init__("RX_MSG", msg_queues, config)
        self.thread_stop = False

    def stop(self):
        self.thread_stop = True
        self.aprs.stop()

    def callback(self, packet):
        try:
            packet = aprslib.parse(packet)
            print(packet)
        except (aprslib.ParseError, aprslib.UnknownFormat):
            pass

    def run(self):
        LOG.info("Starting")
        while not self.thread_stop:
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
        LOG.info("Exiting ")

    def process_ack_packet(self, packet):
        ack_num = packet.get("msgNo")
        LOG.info("Got ack for message {}".format(ack_num))
        messaging.log_message(
            "ACK", packet["raw"], None, ack=ack_num, fromcall=packet["from"]
        )
        messaging.ack_dict.update({int(ack_num): 1})
        return

    def process_mic_e_packet(self, packet):
        LOG.info("Mic-E Packet detected.  Currenlty unsupported.")
        messaging.log_packet(packet)
        return

    def process_message_packet(self, packet):
        LOG.info("Got a message packet")
        fromcall = packet["from"]
        message = packet.get("message_text", None)

        msg_id = packet.get("msgNo", None)
        if not msg_id:
            msg_id = "0"

        messaging.log_message(
            "Received Message", packet["raw"], message, fromcall=fromcall, ack=msg_id
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

                    # msg = {"fromcall": fromcall, "msg": reply}
                    msg = messaging.TextMessage(
                        self.config["aprs"]["login"], fromcall, reply
                    )
                    self.msg_queues["tx"].put(msg)
                else:
                    LOG.debug("Got NULL MESSAGE from plugin")

            if not found_command:
                plugins = pm.get_plugins()
                names = [x.command_name for x in plugins]
                names.sort()

                reply = "Usage: {}".format(", ".join(names))
                # messaging.send_message(fromcall, reply)
                msg = messaging.TextMessage(
                    self.config["aprs"]["login"], fromcall, reply
                )
                self.msg_queues["tx"].put(msg)
        except Exception as ex:
            LOG.exception("Plugin failed!!!", ex)
            reply = "A Plugin failed! try again?"
            # messaging.send_message(fromcall, reply)
            msg = messaging.TextMessage(self.config["aprs"]["login"], fromcall, reply)
            self.msg_queues["tx"].put(msg)

        # let any threads do their thing, then ack
        # send an ack last
        ack = messaging.AckMessage(
            self.config["aprs"]["login"], fromcall, msg_id=msg_id
        )
        ack.send()
        LOG.debug("Packet processing complete")

    def process_packet(self, packet):
        """Process a packet recieved from aprs-is server."""

        LOG.debug("Process packet! {}".format(self.msg_queues))
        try:
            LOG.debug("Got message: {}".format(packet))

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
        super(APRSDTXThread, self).__init__("TX_MSG", msg_queues, config)

    def run(self):
        LOG.info("Starting")
        while not self.thread_stop:
            try:
                msg = self.msg_queues["tx"].get(timeout=0.1)
                LOG.info("TXQ: got message '{}'".format(msg))
                msg.send()
            except queue.Empty:
                pass
        LOG.info("Exiting ")
