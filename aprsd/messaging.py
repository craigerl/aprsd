import abc
import datetime
import logging
from multiprocessing import RawValue
import os
import pathlib
import pickle
import re
import threading
import time

from aprsd import client, threads, utils

LOG = logging.getLogger("APRSD")

# message_nubmer:ack  combos so we stop sending a message after an
# ack from radio {int:int}
# FIXME

# What to return from a plugin if we have processed the message
# and it's ok, but don't send a usage string back
NULL_MESSAGE = -1


class MsgTrack:
    """Class to keep track of outstanding text messages.

    This is a thread safe class that keeps track of active
    messages.

    When a message is asked to be sent, it is placed into this
    class via it's id.  The TextMessage class's send() method
    automatically adds itself to this class.  When the ack is
    recieved from the radio, the message object is removed from
    this class.

    # TODO(hemna)
    When aprsd is asked to quit this class should be serialized and
    saved to disk/db to keep track of the state of outstanding messages.
    When aprsd is started, it should try and fetch the saved state,
    and reloaded to a live state.

    """

    _instance = None
    lock = None

    track = {}
    total_messages_tracked = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.track = {}
            cls._instance.lock = threading.Lock()
        return cls._instance

    def add(self, msg):
        with self.lock:
            key = int(msg.id)
            self.track[key] = msg
            self.total_messages_tracked += 1

    def get(self, id):
        with self.lock:
            if id in self.track:
                return self.track[id]

    def remove(self, id):
        with self.lock:
            key = int(id)
            if key in self.track.keys():
                del self.track[key]

    def __len__(self):
        with self.lock:
            return len(self.track)

    def __str__(self):
        with self.lock:
            result = "{"
            for key in self.track.keys():
                result += "{}: {}, ".format(key, str(self.track[key]))
            result += "}"
            return result

    def save(self):
        """Save this shit to disk?"""
        if len(self) > 0:
            LOG.info("Saving {} tracking messages to disk".format(len(self)))
            pickle.dump(self.dump(), open(utils.DEFAULT_SAVE_FILE, "wb+"))
        else:
            self.flush()

    def dump(self):
        dump = {}
        with self.lock:
            for key in self.track.keys():
                dump[key] = self.track[key]

        return dump

    def load(self):
        if os.path.exists(utils.DEFAULT_SAVE_FILE):
            raw = pickle.load(open(utils.DEFAULT_SAVE_FILE, "rb"))
            if raw:
                self.track = raw
                LOG.debug("Loaded MsgTrack dict from disk.")
                LOG.debug(self)

    def restart(self):
        """Walk the list of messages and restart them if any."""

        for key in self.track.keys():
            msg = self.track[key]
            if msg.last_send_attempt < msg.retry_count:
                msg.send()

    def restart_delayed(self):
        """Walk the list of delayed messages and restart them if any."""
        for key in self.track.keys():
            msg = self.track[key]
            if msg.last_send_attempt == msg.retry_count:
                msg.last_send_attempt = 0
                msg.send()

    def flush(self):
        """Nuke the old pickle file that stored the old results from last aprsd run."""
        if os.path.exists(utils.DEFAULT_SAVE_FILE):
            pathlib.Path(utils.DEFAULT_SAVE_FILE).unlink()
        with self.lock:
            self.track = {}


class MessageCounter:
    """
    Global message id counter class.

    This is a singleton based class that keeps
    an incrementing counter for all messages to
    be sent.  All new Message objects gets a new
    message id, which is the next number available
    from the MessageCounter.

    """

    _instance = None
    max_count = 9999

    def __new__(cls, *args, **kwargs):
        """Make this a singleton class."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.val = RawValue("i", 1)
            cls._instance.lock = threading.Lock()
        return cls._instance

    def increment(self):
        with self.lock:
            if self.val.value == self.max_count:
                self.val.value = 1
            else:
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


class Message(metaclass=abc.ABCMeta):
    """Base Message Class."""

    # The message id to send over the air
    id = 0

    retry_count = 3
    last_send_time = None
    last_send_attempt = 0

    def __init__(self, fromcall, tocall, msg_id=None):
        self.fromcall = fromcall
        self.tocall = tocall
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

    def __init__(self, fromcall, tocall, message, msg_id=None, allow_delay=True):
        super().__init__(fromcall, tocall, msg_id)
        self.message = message
        # do we try and save this message for later if we don't get
        # an ack?  Some messages we don't want to do this ever.
        self.allow_delay = allow_delay

    def __repr__(self):
        """Build raw string to send over the air."""
        return "{}>APRS::{}:{}{{{}\n".format(
            self.fromcall,
            self.tocall.ljust(9),
            self._filter_for_send(),
            str(self.id),
        )

    def __str__(self):
        delta = "Never"
        if self.last_send_time:
            now = datetime.datetime.now()
            delta = now - self.last_send_time
        return "{}>{} Msg({})({}): '{}'".format(
            self.fromcall,
            self.tocall,
            self.id,
            delta,
            self.message,
        )

    def _filter_for_send(self):
        """Filter and format message string for FCC."""
        # max?  ftm400 displays 64, raw msg shows 74
        # and ftm400-send is max 64.  setting this to
        # 67 displays 64 on the ftm400. (+3 {01 suffix)
        # feature req: break long ones into two msgs
        message = self.message[:67]
        # We all miss George Carlin
        return re.sub("fuck|shit|cunt|piss|cock|bitch", "****", message)

    def send(self):
        tracker = MsgTrack()
        tracker.add(self)
        LOG.debug("Length of MsgTrack is {}".format(len(tracker)))
        thread = SendMessageThread(message=self)
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


class SendMessageThread(threads.APRSDThread):
    def __init__(self, message):
        self.msg = message
        name = self.msg.message[:5]
        super().__init__("SendMessage-{}-{}".format(self.msg.id, name))

    def loop(self):
        """Loop until a message is acked or it gets delayed.

        We only sleep for 5 seconds between each loop run, so
        that CTRL-C can exit the app in a short period.  Each sleep
        means the app quitting is blocked until sleep is done.
        So we keep track of the last send attempt and only send if the
        last send attempt is old enough.

        """
        cl = client.get_client()
        tracker = MsgTrack()
        # lets see if the message is still in the tracking queue
        msg = tracker.get(self.msg.id)
        if not msg:
            # The message has been removed from the tracking queue
            # So it got acked and we are done.
            LOG.info("Message Send Complete via Ack.")
            return False
        else:
            send_now = False
            if msg.last_send_attempt == msg.retry_count:
                # we reached the send limit, don't send again
                # TODO(hemna) - Need to put this in a delayed queue?
                LOG.info("Message Send Complete. Max attempts reached.")
                return False

            # Message is still outstanding and needs to be acked.
            if msg.last_send_time:
                # Message has a last send time tracking
                now = datetime.datetime.now()
                sleeptime = (msg.last_send_attempt + 1) * 31
                delta = now - msg.last_send_time
                if delta > datetime.timedelta(seconds=sleeptime):
                    # It's time to try to send it again
                    send_now = True
            else:
                send_now = True

            if send_now:
                # no attempt time, so lets send it, and start
                # tracking the time.
                log_message(
                    "Sending Message",
                    repr(msg).rstrip("\n"),
                    msg.message,
                    tocall=self.msg.tocall,
                    retry_number=msg.last_send_attempt,
                    msg_num=msg.id,
                )
                cl.sendall(repr(msg))
                msg.last_send_time = datetime.datetime.now()
                msg.last_send_attempt += 1

            time.sleep(5)
            # Make sure we get called again.
            return True


class AckMessage(Message):
    """Class for building Acks and sending them."""

    def __init__(self, fromcall, tocall, msg_id):
        super().__init__(fromcall, tocall, msg_id=msg_id)

    def __repr__(self):
        return "{}>APRS::{}:ack{}\n".format(
            self.fromcall,
            self.tocall.ljust(9),
            self.id,
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
        thread = SendAckThread(self)
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


class SendAckThread(threads.APRSDThread):
    def __init__(self, ack):
        self.ack = ack
        super().__init__("SendAck-{}".format(self.ack.id))

    def loop(self):
        """Separate thread to send acks with retries."""
        send_now = False
        if self.ack.last_send_attempt == self.ack.retry_count:
            # we reached the send limit, don't send again
            # TODO(hemna) - Need to put this in a delayed queue?
            LOG.info("Ack Send Complete. Max attempts reached.")
            return False

        if self.ack.last_send_time:
            # Message has a last send time tracking
            now = datetime.datetime.now()

            # aprs duplicate detection is 30 secs?
            # (21 only sends first, 28 skips middle)
            sleeptime = 31
            delta = now - self.ack.last_send_time
            if delta > datetime.timedelta(seconds=sleeptime):
                # It's time to try to send it again
                send_now = True
            else:
                LOG.debug("Still wating. {}".format(delta))
        else:
            send_now = True

        if send_now:
            cl = client.get_client()
            log_message(
                "Sending ack",
                repr(self.ack).rstrip("\n"),
                None,
                ack=self.ack.id,
                tocall=self.ack.tocall,
                retry_number=self.ack.last_send_attempt,
            )
            cl.sendall(repr(self.ack))
            self.ack.last_send_attempt += 1
            self.ack.last_send_time = datetime.datetime.now()
        time.sleep(5)


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
    uuid=None,
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
    if uuid:
        log_list.append("    UUID        : {}".format(uuid))
    # LOG.info("    {} _______________ Complete".format(header))
    log_list.append("    {} _______________ Complete".format(header))

    LOG.info("\n".join(log_list))
