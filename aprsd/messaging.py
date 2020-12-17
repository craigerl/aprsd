import logging
import pprint
import re
import threading
import time

from aprsd import client

LOG = logging.getLogger("APRSD")
CONFIG = None

# current aprs radio message number, increments for each message we
# send over rf {int}
message_number = 0

# message_nubmer:ack  combos so we stop sending a message after an
# ack from radio {int:int}
ack_dict = {}

# What to return from a plugin if we have processed the message
# and it's ok, but don't send a usage string back
NULL_MESSAGE = -1


def send_ack_thread(tocall, ack, retry_count):
    cl = client.get_client()
    tocall = tocall.ljust(9)  # pad to nine chars
    line = "{}>APRS::{}:ack{}\n".format(CONFIG["aprs"]["login"], tocall, ack)
    for i in range(retry_count, 0, -1):
        LOG.info("Sending ack __________________ Tx({})".format(i))
        LOG.info("Raw         : {}".format(line.rstrip("\n")))
        LOG.info("To          : {}".format(tocall))
        LOG.info("Ack number  : {}".format(ack))
        cl.sendall(line)
        # aprs duplicate detection is 30 secs?
        # (21 only sends first, 28 skips middle)
        time.sleep(31)
    # end_send_ack_thread


def send_ack(tocall, ack):
    LOG.debug("Send ACK({}:{}) to radio.".format(tocall, ack))
    retry_count = 3
    thread = threading.Thread(
        target=send_ack_thread, name="send_ack", args=(tocall, ack, retry_count)
    )
    thread.start()
    # end send_ack()


def send_message_thread(tocall, message, this_message_number, retry_count):
    cl = client.get_client()
    line = "{}>APRS::{}:{}{{{}\n".format(
        CONFIG["aprs"]["login"],
        tocall,
        message,
        str(this_message_number),
    )
    for i in range(retry_count, 0, -1):
        LOG.debug("DEBUG: send_message_thread msg:ack combos are: ")
        LOG.debug(pprint.pformat(ack_dict))
        if ack_dict[this_message_number] != 1:
            LOG.info(
                "Sending message_______________ {}(Tx{})".format(
                    str(this_message_number), str(i)
                )
            )
            LOG.info("Raw         : {}".format(line.rstrip("\n")))
            LOG.info("To          : {}".format(tocall))
            # LOG.info("Message     : {}".format(message.encode(errors='ignore')))
            LOG.info("Message     : {}".format(message))
            # tn.write(line)
            cl.sendall(line)
            # decaying repeats, 31 to 93 second intervals
            sleeptime = (retry_count - i + 1) * 31
            time.sleep(sleeptime)
        else:
            break
    return
    # end send_message_thread


def send_message(tocall, message):
    global message_number
    global ack_dict

    retry_count = 3
    if message_number > 98:  # global
        message_number = 0
    message_number += 1
    if len(ack_dict) > 90:
        # empty ack dict if it's really big, could result in key error later
        LOG.debug(
            "DEBUG: Length of ack dictionary is big at %s clearing." % len(ack_dict)
        )
        ack_dict.clear()
        LOG.debug(pprint.pformat(ack_dict))
        LOG.debug(
            "DEBUG: Cleared ack dictionary, ack_dict length is now %s." % len(ack_dict)
        )
    ack_dict[message_number] = 0  # clear ack for this message number
    tocall = tocall.ljust(9)  # pad to nine chars

    # max?  ftm400 displays 64, raw msg shows 74
    # and ftm400-send is max 64.  setting this to
    # 67 displays 64 on the ftm400. (+3 {01 suffix)
    # feature req: break long ones into two msgs
    message = message[:67]
    # We all miss George Carlin
    message = re.sub("fuck|shit|cunt|piss|cock|bitch", "****", message)
    thread = threading.Thread(
        target=send_message_thread,
        name="send_message",
        args=(tocall, message, message_number, retry_count),
    )
    thread.start()
    return ()
    # end send_message()


def process_message(line):
    f = re.search("^(.*)>", line)
    fromcall = f.group(1)
    searchstring = "::%s[ ]*:(.*)" % CONFIG["aprs"]["login"]
    # verify this, callsign is padded out with spaces to colon
    m = re.search(searchstring, line)
    fullmessage = m.group(1)

    ack_attached = re.search("(.*){([0-9A-Z]+)", fullmessage)
    # ack formats include: {1, {AB}, {12
    if ack_attached:
        # "{##" suffix means radio wants an ack back
        # message content
        message = ack_attached.group(1)
        # suffix number to use in ack
        ack_num = ack_attached.group(2)
    else:
        message = fullmessage
        # ack not requested, but lets send one as 0
        ack_num = "0"

    LOG.info("Received message______________")
    LOG.info("Raw         : " + line)
    LOG.info("From        : " + fromcall)
    LOG.info("Message     : " + message)
    LOG.info("Msg number  : " + str(ack_num))

    return (fromcall, message, ack_num)
    # end process_message()
