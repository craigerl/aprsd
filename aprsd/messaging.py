import abc
import datetime
import logging
from multiprocessing import RawValue
import re
import threading
import time

from aprsd import client, objectstore, packets, stats, threads


LOG = logging.getLogger("APRSD")

# What to return from a plugin if we have processed the message
# and it's ok, but don't send a usage string back
NULL_MESSAGE = -1


class MsgTrack(objectstore.ObjectStoreMixin):
    """Class to keep track of outstanding text messages.

    This is a thread safe class that keeps track of active
    messages.

    When a message is asked to be sent, it is placed into this
    class via it's id.  The TextMessage class's send() method
    automatically adds itself to this class.  When the ack is
    recieved from the radio, the message object is removed from
    this class.
    """

    _instance = None
    _start_time = None
    lock = None

    data = {}
    total_messages_tracked = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.track = {}
            cls._instance._start_time = datetime.datetime.now()
            cls._instance.lock = threading.Lock()
            cls._instance.config = kwargs["config"]
            cls._instance._init_store()
        return cls._instance

    def __getitem__(self, name):
        with self.lock:
            return self.data[name]

    def __iter__(self):
        with self.lock:
            return iter(self.data)

    def keys(self):
        with self.lock:
            return self.data.keys()

    def items(self):
        with self.lock:
            return self.data.items()

    def values(self):
        with self.lock:
            return self.data.values()

    def __len__(self):
        with self.lock:
            return len(self.data)

    def __str__(self):
        with self.lock:
            result = "{"
            for key in self.data.keys():
                result += f"{key}: {str(self.data[key])}, "
            result += "}"
            return result

    def add(self, msg):
        with self.lock:
            key = int(msg.id)
            self.data[key] = msg
            stats.APRSDStats().msgs_tracked_inc()
            self.total_messages_tracked += 1

    def get(self, id):
        with self.lock:
            if id in self.data:
                return self.data[id]

    def remove(self, id):
        with self.lock:
            key = int(id)
            if key in self.data.keys():
                del self.data[key]

    def restart(self):
        """Walk the list of messages and restart them if any."""

        for key in self.data.keys():
            msg = self.data[key]
            if msg.last_send_attempt < msg.retry_count:
                msg.send()

    def _resend(self, msg):
        msg.last_send_attempt = 0
        msg.send()

    def restart_delayed(self, count=None, most_recent=True):
        """Walk the list of delayed messages and restart them if any."""
        if not count:
            # Send all the delayed messages
            for key in self.data.keys():
                msg = self.data[key]
                if msg.last_send_attempt == msg.retry_count:
                    self._resend(msg)
        else:
            # They want to resend <count> delayed messages
            tmp = sorted(
                self.data.items(),
                reverse=most_recent,
                key=lambda x: x[1].last_send_time,
            )
            msg_list = tmp[:count]
            for (_key, msg) in msg_list:
                self._resend(msg)


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
    lock = None

    def __new__(cls, *args, **kwargs):
        """Make this a singleton class."""
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
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
    last_send_time = 0
    last_send_attempt = 0

    transport = None

    def __init__(
        self,
        fromcall,
        tocall,
        msg_id=None,
    ):
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


class RawMessage(Message):
    """Send a raw message.

    This class is used for custom messages that contain the entire
    contents of an APRS message in the message field.

    """

    message = None

    def __init__(self, message):
        super().__init__(None, None, msg_id=None)
        self.message = message

    def dict(self):
        now = datetime.datetime.now()
        last_send_age = None
        if self.last_send_time:
            last_send_age = str(now - self.last_send_time)
        return {
            "type": "raw",
            "message": self.message.rstrip("\n"),
            "raw": self.message.rstrip("\n"),
            "retry_count": self.retry_count,
            "last_send_attempt": self.last_send_attempt,
            "last_send_time": str(self.last_send_time),
            "last_send_age": last_send_age,
        }

    def __str__(self):
        return self.message

    def send(self):
        tracker = MsgTrack()
        tracker.add(self)
        thread = SendMessageThread(message=self)
        thread.start()

    def send_direct(self, aprsis_client=None):
        """Send a message without a separate thread."""
        cl = client.factory.create().client
        log_message(
            "Sending Message Direct",
            str(self).rstrip("\n"),
            self.message,
            tocall=self.tocall,
            fromcall=self.fromcall,
        )
        cl.send(self)
        stats.APRSDStats().msgs_tx_inc()


class TextMessage(Message):
    """Send regular ARPS text/command messages/replies."""

    message = None

    def __init__(
        self,
        fromcall,
        tocall,
        message,
        msg_id=None,
        allow_delay=True,
    ):
        super().__init__(fromcall, tocall, msg_id)
        self.message = message
        # do we try and save this message for later if we don't get
        # an ack?  Some messages we don't want to do this ever.
        self.allow_delay = allow_delay

    def dict(self):
        now = datetime.datetime.now()

        last_send_age = None
        if self.last_send_time:
            last_send_age = str(now - self.last_send_time)

        return {
            "id": self.id,
            "type": "text-message",
            "fromcall": self.fromcall,
            "tocall": self.tocall,
            "message": self.message.rstrip("\n"),
            "raw": str(self).rstrip("\n"),
            "retry_count": self.retry_count,
            "last_send_attempt": self.last_send_attempt,
            "last_send_time": str(self.last_send_time),
            "last_send_age": last_send_age,
        }

    def __str__(self):
        """Build raw string to send over the air."""
        return "{}>APZ100::{}:{}{{{}\n".format(
            self.fromcall,
            self.tocall.ljust(9),
            self._filter_for_send(),
            str(self.id),
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
        LOG.debug(f"Length of MsgTrack is {len(tracker)}")
        thread = SendMessageThread(message=self)
        thread.start()

    def send_direct(self, aprsis_client=None):
        """Send a message without a separate thread."""
        if aprsis_client:
            cl = aprsis_client
        else:
            cl = client.factory.create().client
        log_message(
            "Sending Message Direct",
            str(self).rstrip("\n"),
            self.message,
            tocall=self.tocall,
            fromcall=self.fromcall,
        )
        cl.send(self)
        stats.APRSDStats().msgs_tx_inc()
        packets.PacketList().add(self.dict())


class SendMessageThread(threads.APRSDThread):
    def __init__(self, message):
        self.msg = message
        name = self.msg.message[:5]
        super().__init__(f"SendMessage-{self.msg.id}-{name}")

    def loop(self):
        """Loop until a message is acked or it gets delayed.

        We only sleep for 5 seconds between each loop run, so
        that CTRL-C can exit the app in a short period.  Each sleep
        means the app quitting is blocked until sleep is done.
        So we keep track of the last send attempt and only send if the
        last send attempt is old enough.

        """
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
                    str(msg).rstrip("\n"),
                    msg.message,
                    tocall=self.msg.tocall,
                    retry_number=msg.last_send_attempt,
                    msg_num=msg.id,
                )
                cl = client.factory.create().client
                cl.send(msg)
                stats.APRSDStats().msgs_tx_inc()
                packets.PacketList().add(msg.dict())
                msg.last_send_time = datetime.datetime.now()
                msg.last_send_attempt += 1

            time.sleep(5)
            # Make sure we get called again.
            return True


class AckMessage(Message):
    """Class for building Acks and sending them."""

    def __init__(self, fromcall, tocall, msg_id):
        super().__init__(fromcall, tocall, msg_id=msg_id)

    def dict(self):
        now = datetime.datetime.now()
        last_send_age = None
        if self.last_send_time:
            last_send_age = str(now - self.last_send_time)
        return {
            "id": self.id,
            "type": "ack",
            "fromcall": self.fromcall,
            "tocall": self.tocall,
            "raw": str(self).rstrip("\n"),
            "retry_count": self.retry_count,
            "last_send_attempt": self.last_send_attempt,
            "last_send_time": str(self.last_send_time),
            "last_send_age": last_send_age,
        }

    def __str__(self):
        return "{}>APZ100::{}:ack{}\n".format(
            self.fromcall,
            self.tocall.ljust(9),
            self.id,
        )

    def _filter_for_send(self):
        return f"ack{self.id}"

    def send(self):
        LOG.debug(f"Send ACK({self.tocall}:{self.id}) to radio.")
        thread = SendAckThread(self)
        thread.start()

    def send_direct(self, aprsis_client=None):
        """Send an ack message without a separate thread."""
        if aprsis_client:
            cl = aprsis_client
        else:
            cl = client.factory.create().client
        log_message(
            "Sending ack",
            str(self).rstrip("\n"),
            None,
            ack=self.id,
            tocall=self.tocall,
            fromcall=self.fromcall,
        )
        cl.send(self)


class SendAckThread(threads.APRSDThread):
    def __init__(self, ack):
        self.ack = ack
        super().__init__(f"SendAck-{self.ack.id}")

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
                LOG.debug(f"Still wating. {delta}")
        else:
            send_now = True

        if send_now:
            cl = client.factory.create().client
            log_message(
                "Sending ack",
                str(self.ack).rstrip("\n"),
                None,
                ack=self.ack.id,
                tocall=self.ack.tocall,
                retry_number=self.ack.last_send_attempt,
            )
            cl.send(self.ack)
            stats.APRSDStats().ack_tx_inc()
            packets.PacketList().add(self.ack.dict())
            self.ack.last_send_attempt += 1
            self.ack.last_send_time = datetime.datetime.now()
        time.sleep(5)
        return True


def log_packet(packet):
    fromcall = packet.get("from", None)
    tocall = packet.get("to", None)

    response_type = packet.get("response", None)
    msg = packet.get("message_text", None)
    msg_num = packet.get("msgNo", None)
    ack = packet.get("ack", None)

    log_message(
        "Packet", packet["raw"], msg, fromcall=fromcall, tocall=tocall,
        ack=ack, packet_type=response_type, msg_num=msg_num, )


def log_message(
    header, raw, message, tocall=None, fromcall=None, msg_num=None,
    retry_number=None, ack=None, packet_type=None, uuid=None,
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
        log_list.append(f"    {header} _______________(TX:{retry_number})")
    else:
        # LOG.info("    {} _______________".format(header))
        log_list.append(f"    {header} _______________")

    # LOG.info("    Raw         : {}".format(raw))
    log_list.append(f"    Raw         : {raw}")

    if packet_type:
        # LOG.info("    Packet      : {}".format(packet_type))
        log_list.append(f"    Packet      : {packet_type}")
    if tocall:
        # LOG.info("    To          : {}".format(tocall))
        log_list.append(f"    To          : {tocall}")
    if fromcall:
        # LOG.info("    From        : {}".format(fromcall))
        log_list.append(f"    From        : {fromcall}")

    if ack:
        # LOG.info("    Ack         : {}".format(ack))
        log_list.append(f"    Ack         : {ack}")
    else:
        # LOG.info("    Message     : {}".format(message))
        log_list.append(f"    Message     : {message}")
    if msg_num:
        # LOG.info("    Msg number  : {}".format(msg_num))
        log_list.append(f"    Msg number  : {msg_num}")
    if uuid:
        log_list.append(f"    UUID        : {uuid}")
    # LOG.info("    {} _______________ Complete".format(header))
    log_list.append(f"    {header} _______________ Complete")

    LOG.info("\n".join(log_list))
