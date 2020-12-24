import abc
import logging
import pprint
import re
import threading
import time
import uuid
from multiprocessing import RawValue

from aprsd import client

LOG = logging.getLogger("APRSD")

# message_nubmer:ack  combos so we stop sending a message after an
# ack from radio {int:int}
# FIXME
ack_dict = {}

# What to return from a plugin if we have processed the message
# and it's ok, but don't send a usage string back
NULL_MESSAGE = -1


class MessageCounter(object):
    """
    Global message id counter class.

    This is a singleton based class that keeps
    an incrementing counter for all messages to
    be sent.  All new Message objects gets a new
    message id, which is the next number available
    from the MessageCounter.

    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Make this a singleton class."""
        if cls._instance is None:
            cls._instance = super(MessageCounter, cls).__new__(cls)
            cls._instance.val = RawValue("i", 1)
            cls._instance.lock = threading.Lock()
        return cls._instance

    def increment(self):
        with self.lock:
            self.val.value += 1

    @property
    def value(self):
        with self.lock:
            return self.val.value

    def __repr__(self):
        with self.lock:
            return str(self.val.value)

    def __str__(self):
        with self.lock:
            return str(self.val.value)


class Message(object, metaclass=abc.ABCMeta):
    """Base Message Class."""

    # The message id to send over the air
    id = 0

    # Unique identifier for this message
    uuid = None

    sent = False
    sent_time = None
    acked = False
    acked_time = None

    retry_count = 3

    def __init__(self, fromcall, tocall, msg_id=None):
        self.fromcall = fromcall
        self.tocall = tocall
        self.uuid = uuid.uuid4()
        if not msg_id:
            c = MessageCounter()
            c.increment()
            msg_id = c.value
        self.id = msg_id

    @abc.abstractmethod
    def send(self):
        """Child class must declare."""
        pass


class TextMessage(Message):
    """Send regular ARPS text/command messages/replies."""

    message = None

    def __init__(self, fromcall, tocall, message):
        super(TextMessage, self).__init__(fromcall, tocall)
        self.message = message

    def __repr__(self):
        """Build raw string to send over the air."""
        return "{}>APRS::{}:{}{{{}\n".format(
            self.fromcall,
            self.tocall.ljust(9),
            self._filter_for_send(),
            str(self.id),
        )

    def __str__(self):
        return "From({}) TO({}) - Message({}): '{}'".format(
            self.fromcall, self.tocall, self.id, self.message
        )

    def ack(self):
        """Build an Ack Message object from this object."""
        return AckMessage(self.fromcall, self.tocall, msg_id=self.id)

    def _filter_for_send(self):
        """Filter and format message string for FCC."""
        # max?  ftm400 displays 64, raw msg shows 74
        # and ftm400-send is max 64.  setting this to
        # 67 displays 64 on the ftm400. (+3 {01 suffix)
        # feature req: break long ones into two msgs
        message = self.message[:67]
        # We all miss George Carlin
        return re.sub("fuck|shit|cunt|piss|cock|bitch", "****", message)

    def send_thread(self):
        cl = client.get_client()
        for i in range(self.retry_count, 0, -1):
            LOG.debug("DEBUG: send_message_thread msg:ack combos are: ")
            LOG.debug(pprint.pformat(ack_dict))
            if ack_dict[self.id] != 1:
                log_message(
                    "Sending Message",
                    repr(self).rstrip("\n"),
                    self.message,
                    tocall=self.tocall,
                    retry_number=i,
                )
                # tn.write(line)
                cl.sendall(repr(self))
                # decaying repeats, 31 to 93 second intervals
                sleeptime = (self.retry_count - i + 1) * 31
                time.sleep(sleeptime)
            else:
                break
        return
        # end send_message_thread

    def send(self):
        global ack_dict

        # TODO(Hemna) - Need a better metchanism for this.
        # This can nuke an ack_dict while it's still being used.
        # FIXME FIXME
        if len(ack_dict) > 90:
            # empty ack dict if it's really big, could result in key error later
            LOG.debug(
                "DEBUG: Length of ack dictionary is big at %s clearing." % len(ack_dict)
            )
            ack_dict.clear()
            LOG.debug(pprint.pformat(ack_dict))
            LOG.debug(
                "DEBUG: Cleared ack dictionary, ack_dict length is now %s."
                % len(ack_dict)
            )
        ack_dict[self.id] = 0  # clear ack for this message number

        thread = threading.Thread(target=self.send_thread, name="send_message")
        thread.start()

    def send_direct(self):
        """Send a message without a separate thread."""
        cl = client.get_client()
        log_message(
            "Sending Message Direct",
            repr(self).rstrip("\n"),
            self.message,
            tocall=self.tocall,
            fromcall=self.fromcall,
        )
        cl.sendall(repr(self))


class AckMessage(Message):
    """Class for building Acks and sending them."""

    def __init__(self, fromcall, tocall, msg_id):
        super(AckMessage, self).__init__(fromcall, tocall, msg_id=msg_id)

    def __repr__(self):
        return "{}>APRS::{}:ack{}\n".format(
            self.fromcall, self.tocall.ljust(9), self.id
        )

    def __str__(self):
        return "From({}) TO({}) Ack ({})".format(self.fromcall, self.tocall, self.id)

    def send_thread(self):
        """Separate thread to send acks with retries."""
        cl = client.get_client()
        for i in range(self.retry_count, 0, -1):
            log_message(
                "Sending ack",
                repr(self).rstrip("\n"),
                None,
                ack=self.id,
                tocall=self.tocall,
                retry_number=i,
            )
            cl.sendall(repr(self))
            # aprs duplicate detection is 30 secs?
            # (21 only sends first, 28 skips middle)
            time.sleep(31)
        # end_send_ack_thread

    def send(self):
        LOG.debug("Send ACK({}:{}) to radio.".format(self.tocall, self.id))
        thread = threading.Thread(target=self.send_thread, name="send_ack")
        thread.start()

    # end send_ack()

    def send_direct(self):
        """Send an ack message without a separate thread."""
        cl = client.get_client()
        log_message(
            "Sending ack",
            repr(self).rstrip("\n"),
            None,
            ack=self.id,
            tocall=self.tocall,
            fromcall=self.fromcall,
        )
        cl.sendall(repr(self))


def log_packet(packet):
    fromcall = packet.get("from", None)
    tocall = packet.get("to", None)

    response_type = packet.get("response", None)
    msg = packet.get("message_text", None)
    msg_num = packet.get("msgNo", None)
    ack = packet.get("ack", None)

    log_message(
        "Packet",
        packet["raw"],
        msg,
        fromcall=fromcall,
        tocall=tocall,
        ack=ack,
        packet_type=response_type,
        msg_num=msg_num,
    )


def log_message(
    header,
    raw,
    message,
    tocall=None,
    fromcall=None,
    msg_num=None,
    retry_number=None,
    ack=None,
    packet_type=None,
):
    """

    Log a message entry.

    This builds a long string with newlines for the log entry, so that
    it's thread safe.   If we log each item as a separate log.debug() call
    Then the message information could get multiplexed with other log
    messages.  Each python log call is automatically synchronized.


    """

    log_list = [""]
    if retry_number:
        # LOG.info("    {} _______________(TX:{})".format(header, retry_number))
        log_list.append("    {} _______________(TX:{})".format(header, retry_number))
    else:
        # LOG.info("    {} _______________".format(header))
        log_list.append("    {} _______________".format(header))

    # LOG.info("    Raw         : {}".format(raw))
    log_list.append("    Raw         : {}".format(raw))

    if packet_type:
        # LOG.info("    Packet      : {}".format(packet_type))
        log_list.append("    Packet      : {}".format(packet_type))
    if tocall:
        # LOG.info("    To          : {}".format(tocall))
        log_list.append("    To          : {}".format(tocall))
    if fromcall:
        # LOG.info("    From        : {}".format(fromcall))
        log_list.append("    From        : {}".format(fromcall))

    if ack:
        # LOG.info("    Ack         : {}".format(ack))
        log_list.append("    Ack         : {}".format(ack))
    else:
        # LOG.info("    Message     : {}".format(message))
        log_list.append("    Message     : {}".format(message))
    if msg_num:
        # LOG.info("    Msg number  : {}".format(msg_num))
        log_list.append("    Msg number  : {}".format(msg_num))
    # LOG.info("    {} _______________ Complete".format(header))
    log_list.append("    {} _______________ Complete".format(header))

    LOG.info("\n".join(log_list))
