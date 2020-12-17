import datetime
import email
import imaplib
import logging
import re
import smtplib
import threading
import time
from email.mime.text import MIMEText

import imapclient
import six

from aprsd import messaging

LOG = logging.getLogger("APRSD")

# This gets forced set from main.py prior to being used internally
CONFIG = None


def start_thread():
    checkemailthread = threading.Thread(
        target=check_email_thread, name="check_email", args=()
    )  # args must be tuple
    checkemailthread.start()


def _imap_connect():
    imap_port = CONFIG["imap"].get("port", 143)
    use_ssl = CONFIG["imap"].get("use_ssl", False)
    host = CONFIG["imap"]["host"]
    msg = "{}{}:{}".format("TLS " if use_ssl else "", host, imap_port)
    #    LOG.debug("Connect to IMAP host {} with user '{}'".
    #              format(msg, CONFIG['imap']['login']))

    try:
        server = imapclient.IMAPClient(
            CONFIG["imap"]["host"], port=imap_port, use_uid=True, ssl=use_ssl
        )
    except Exception:
        LOG.error("Failed to connect IMAP server")
        return

    try:
        server.login(CONFIG["imap"]["login"], CONFIG["imap"]["password"])
    except (imaplib.IMAP4.error, Exception) as e:
        msg = getattr(e, "message", repr(e))
        LOG.error("Failed to login {}".format(msg))
        return

    server.select_folder("INBOX")
    return server


def _smtp_connect():
    host = CONFIG["smtp"]["host"]
    smtp_port = CONFIG["smtp"]["port"]
    use_ssl = CONFIG["smtp"].get("use_ssl", False)
    msg = "{}{}:{}".format("SSL " if use_ssl else "", host, smtp_port)
    LOG.debug(
        "Connect to SMTP host {} with user '{}'".format(msg, CONFIG["imap"]["login"])
    )

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host=host, port=smtp_port)
        else:
            server = smtplib.SMTP(host=host, port=smtp_port)
    except Exception:
        LOG.error("Couldn't connect to SMTP Server")
        return

    LOG.debug("Connected to smtp host {}".format(msg))

    try:
        server.login(CONFIG["smtp"]["login"], CONFIG["smtp"]["password"])
    except Exception:
        LOG.error("Couldn't connect to SMTP Server")
        return

    LOG.debug("Logged into SMTP server {}".format(msg))
    return server


def validate_email():
    """function to simply ensure we can connect to email services.

    This helps with failing early during startup.
    """
    LOG.info("Checking IMAP configuration")
    imap_server = _imap_connect()
    LOG.info("Checking SMTP configuration")
    smtp_server = _smtp_connect()

    if imap_server and smtp_server:
        return True
    else:
        return False


def parse_email(msgid, data, server):
    envelope = data[b"ENVELOPE"]
    # email address match
    # use raw string to avoid invalid escape secquence errors r"string here"
    f = re.search(r"([\.\w_-]+@[\.\w_-]+)", str(envelope.from_[0]))
    if f is not None:
        from_addr = f.group(1)
    else:
        from_addr = "noaddr"
    LOG.debug("Got a message from '{}'".format(from_addr))
    m = server.fetch([msgid], ["RFC822"])
    msg = email.message_from_string(m[msgid][b"RFC822"].decode(errors="ignore"))
    if msg.is_multipart():
        text = ""
        html = None
        # default in case body somehow isn't set below - happened once
        body = b"* unreadable msg received"
        # this uses the last text or html part in the email, phone companies often put content in an attachment
        for part in msg.get_payload():
            if part.get_content_charset() is None:
                # or BREAK when we hit a text or html?
                # We cannot know the character set,
                # so return decoded "something"
                LOG.debug("Email got unknown content type")
                text = part.get_payload(decode=True)
                continue

            charset = part.get_content_charset()

            if part.get_content_type() == "text/plain":
                LOG.debug("Email got text/plain")
                text = six.text_type(
                    part.get_payload(decode=True), str(charset), "ignore"
                ).encode("utf8", "replace")

            if part.get_content_type() == "text/html":
                LOG.debug("Email got text/html")
                html = six.text_type(
                    part.get_payload(decode=True), str(charset), "ignore"
                ).encode("utf8", "replace")

            if text is not None:
                # strip removes white space fore and aft of string
                body = text.strip()
            else:
                body = html.strip()
    else:  # message is not multipart
        # email.uscc.net sends no charset, blows up unicode function below
        LOG.debug("Email is not multipart")
        if msg.get_content_charset() is None:
            text = six.text_type(
                msg.get_payload(decode=True), "US-ASCII", "ignore"
            ).encode("utf8", "replace")
        else:
            text = six.text_type(
                msg.get_payload(decode=True), msg.get_content_charset(), "ignore"
            ).encode("utf8", "replace")
        body = text.strip()

    # FIXED:  UnicodeDecodeError: 'ascii' codec can't decode byte 0xf0 in position 6: ordinal not in range(128)
    #  decode with errors='ignore'.   be sure to encode it before we return it below, also with errors='ignore'
    try:
        body = body.decode(errors="ignore")
    except Exception as e:
        LOG.error("Unicode decode failure:  " + str(e))
        LOG.error("Unidoce decode failed: " + str(body))
        body = "Unreadable unicode msg"
    # strip all html tags
    body = re.sub("<[^<]+?>", "", body)
    # strip CR/LF, make it one line, .rstrip fails at this
    body = body.replace("\n", " ").replace("\r", " ")
    # ascii might be out of range, so encode it, removing any error characters
    body = body.encode(errors="ignore")
    return (body, from_addr)


# end parse_email


def resend_email(count, fromcall):
    global check_email_delay
    date = datetime.datetime.now()
    month = date.strftime("%B")[:3]  # Nov, Mar, Apr
    day = date.day
    year = date.year
    today = "%s-%s-%s" % (day, month, year)

    shortcuts = CONFIG["shortcuts"]
    # swap key/value
    shortcuts_inverted = dict([[v, k] for k, v in shortcuts.items()])

    try:
        server = _imap_connect()
    except Exception as e:
        LOG.exception("Failed to Connect to IMAP. Cannot resend email ", e)
        return

    messages = server.search(["SINCE", today])
    # LOG.debug("%d messages received today" % len(messages))

    msgexists = False

    messages.sort(reverse=True)
    del messages[int(count) :]  # only the latest "count" messages
    for message in messages:
        for msgid, data in list(server.fetch(message, ["ENVELOPE"]).items()):
            # one at a time, otherwise order is random
            (body, from_addr) = parse_email(msgid, data, server)
            # unset seen flag, will stay bold in email client
            server.remove_flags(msgid, [imapclient.SEEN])
            if from_addr in shortcuts_inverted:
                # reverse lookup of a shortcut
                from_addr = shortcuts_inverted[from_addr]
            # asterisk indicates a resend
            reply = "-" + from_addr + " * " + body.decode(errors="ignore")
            messaging.send_message(fromcall, reply)
            msgexists = True

    if msgexists is not True:
        stm = time.localtime()
        h = stm.tm_hour
        m = stm.tm_min
        s = stm.tm_sec
        # append time as a kind of serial number to prevent FT1XDR from
        # thinking this is a duplicate message.
        # The FT1XDR pretty much ignores the aprs message number in this
        # regard.  The FTM400 gets it right.
        reply = "No new msg %s:%s:%s" % (
            str(h).zfill(2),
            str(m).zfill(2),
            str(s).zfill(2),
        )
        messaging.send_message(fromcall, reply)

    # check email more often since we're resending one now
    check_email_delay = 60

    server.logout()
    # end resend_email()


def check_email_thread():
    global check_email_delay

    # LOG.debug("FIXME initial email delay is 10 seconds")
    check_email_delay = 60
    while True:
        #        LOG.debug("Top of check_email_thread.")

        time.sleep(check_email_delay)

        # slowly increase delay every iteration, max out at 300 seconds
        # any send/receive/resend activity will reset this to 60 seconds
        if check_email_delay < 300:
            check_email_delay += 1
        LOG.debug("check_email_delay is " + str(check_email_delay) + " seconds")

        shortcuts = CONFIG["shortcuts"]
        # swap key/value
        shortcuts_inverted = dict([[v, k] for k, v in shortcuts.items()])

        date = datetime.datetime.now()
        month = date.strftime("%B")[:3]  # Nov, Mar, Apr
        day = date.day
        year = date.year
        today = "%s-%s-%s" % (day, month, year)

        server = None
        try:
            server = _imap_connect()
        except Exception as e:
            LOG.exception("Failed to get IMAP server Can't check email.", e)

        if not server:
            continue

        messages = server.search(["SINCE", today])
        # LOG.debug("{} messages received today".format(len(messages)))

        for msgid, data in server.fetch(messages, ["ENVELOPE"]).items():
            envelope = data[b"ENVELOPE"]
            # LOG.debug('ID:%d  "%s" (%s)' % (msgid, envelope.subject.decode(), envelope.date))
            f = re.search(
                r"'([[A-a][0-9]_-]+@[[A-a][0-9]_-\.]+)", str(envelope.from_[0])
            )
            if f is not None:
                from_addr = f.group(1)
            else:
                from_addr = "noaddr"

            # LOG.debug("Message flags/tags:  " + str(server.get_flags(msgid)[msgid]))
            # if "APRS" not in server.get_flags(msgid)[msgid]:
            # in python3, imap tags are unicode.  in py2 they're strings. so .decode them to handle both
            taglist = [
                x.decode(errors="ignore") for x in server.get_flags(msgid)[msgid]
            ]
            if "APRS" not in taglist:
                # if msg not flagged as sent via aprs
                server.fetch([msgid], ["RFC822"])
                (body, from_addr) = parse_email(msgid, data, server)
                # unset seen flag, will stay bold in email client
                server.remove_flags(msgid, [imapclient.SEEN])

                if from_addr in shortcuts_inverted:
                    # reverse lookup of a shortcut
                    from_addr = shortcuts_inverted[from_addr]

                reply = "-" + from_addr + " " + body.decode(errors="ignore")
                messaging.send_message(CONFIG["ham"]["callsign"], reply)
                # flag message as sent via aprs
                server.add_flags(msgid, ["APRS"])
                # unset seen flag, will stay bold in email client
                server.remove_flags(msgid, [imapclient.SEEN])
                # check email more often since we just received an email
                check_email_delay = 60

        server.logout()


# end check_email()


def send_email(to_addr, content):
    global check_email_delay

    LOG.info("Sending Email_________________")
    shortcuts = CONFIG["shortcuts"]
    if to_addr in shortcuts:
        LOG.info("To          : " + to_addr)
        to_addr = shortcuts[to_addr]
        LOG.info(" (" + to_addr + ")")
    subject = CONFIG["ham"]["callsign"]
    # content = content + "\n\n(NOTE: reply with one line)"
    LOG.info("Subject     : " + subject)
    LOG.info("Body        : " + content)

    # check email more often since there's activity right now
    check_email_delay = 60

    msg = MIMEText(content)
    msg["Subject"] = subject
    msg["From"] = CONFIG["smtp"]["login"]
    msg["To"] = to_addr
    server = _smtp_connect()
    if server:
        try:
            server.sendmail(CONFIG["smtp"]["login"], [to_addr], msg.as_string())
        except Exception as e:
            msg = getattr(e, "message", repr(e))
            LOG.error("Sendmail Error!!!! '{}'", msg)
            server.quit()
            return -1
        server.quit()
        return 0
    # end send_email
