import datetime
import email
from email.mime.text import MIMEText
import imaplib
import logging
import re
import smtplib
import time

from aprsd import messaging, threads
import imapclient
from validate_email import validate_email

LOG = logging.getLogger("APRSD")

# This gets forced set from main.py prior to being used internally
CONFIG = None


def _imap_connect():
    imap_port = CONFIG["imap"].get("port", 143)
    use_ssl = CONFIG["imap"].get("use_ssl", False)
    host = CONFIG["imap"]["host"]
    msg = "{}{}:{}".format("TLS " if use_ssl else "", host, imap_port)
    #    LOG.debug("Connect to IMAP host {} with user '{}'".
    #              format(msg, CONFIG['imap']['login']))

    try:
        server = imapclient.IMAPClient(
            CONFIG["imap"]["host"],
            port=imap_port,
            use_uid=True,
            ssl=use_ssl,
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
        "Connect to SMTP host {} with user '{}'".format(msg, CONFIG["imap"]["login"]),
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


def validate_shortcuts(config):
    shortcuts = config.get("shortcuts", None)
    if not shortcuts:
        return

    LOG.info(
        "Validating {} Email shortcuts. This can take up to 10 seconds"
        " per shortcut".format(len(shortcuts)),
    )
    delete_keys = []
    for key in shortcuts:
        is_valid = validate_email(
            email_address=shortcuts[key],
            check_regex=True,
            check_mx=True,
            from_address=config["smtp"]["login"],
            helo_host=config["smtp"]["host"],
            smtp_timeout=10,
            dns_timeout=10,
            use_blacklist=False,
            debug=False,
        )
        if not is_valid:
            LOG.error(
                "'{}' is an invalid email address. Removing shortcut".format(
                    shortcuts[key],
                ),
            )
            delete_keys.append(key)

    for key in delete_keys:
        del config["shortcuts"][key]

    LOG.info("Available shortcuts: {}".format(config["shortcuts"]))


def get_email_from_shortcut(shortcut):
    if shortcut in CONFIG.get("shortcuts", None):
        return CONFIG["shortcuts"].get(shortcut, None)


def validate_email_config(config, disable_validation=False):
    """function to simply ensure we can connect to email services.

    This helps with failing early during startup.
    """
    LOG.info("Checking IMAP configuration")
    imap_server = _imap_connect()
    LOG.info("Checking SMTP configuration")
    smtp_server = _smtp_connect()

    # Now validate and flag any shortcuts as invalid
    if not disable_validation:
        validate_shortcuts(config)
    else:
        LOG.info("Shortcuts email validation is Disabled!!, you were warned.")

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
                text = str(
                    part.get_payload(decode=True),
                    str(charset),
                    "ignore",
                ).encode("utf8", "replace")

            if part.get_content_type() == "text/html":
                LOG.debug("Email got text/html")
                html = str(
                    part.get_payload(decode=True),
                    str(charset),
                    "ignore",
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
            text = str(msg.get_payload(decode=True), "US-ASCII", "ignore").encode(
                "utf8",
                "replace",
            )
        else:
            text = str(
                msg.get_payload(decode=True),
                msg.get_content_charset(),
                "ignore",
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


def send_email(to_addr, content):
    global check_email_delay

    shortcuts = CONFIG["shortcuts"]
    email_address = get_email_from_shortcut(to_addr)
    LOG.info("Sending Email_________________")

    if to_addr in shortcuts:
        LOG.info("To          : " + to_addr)
        to_addr = email_address
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


def resend_email(count, fromcall):
    global check_email_delay
    date = datetime.datetime.now()
    month = date.strftime("%B")[:3]  # Nov, Mar, Apr
    day = date.day
    year = date.year
    today = "{}-{}-{}".format(day, month, year)

    shortcuts = CONFIG["shortcuts"]
    # swap key/value
    shortcuts_inverted = {v: k for k, v in shortcuts.items()}

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
            # messaging.send_message(fromcall, reply)
            msg = messaging.TextMessage(CONFIG["aprs"]["login"], fromcall, reply)
            msg.send()
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
        reply = "No new msg {}:{}:{}".format(
            str(h).zfill(2),
            str(m).zfill(2),
            str(s).zfill(2),
        )
        # messaging.send_message(fromcall, reply)
        msg = messaging.TextMessage(CONFIG["aprs"]["login"], fromcall, reply)
        msg.send()

    # check email more often since we're resending one now
    check_email_delay = 60

    server.logout()
    # end resend_email()


class APRSDEmailThread(threads.APRSDThread):
    def __init__(self, msg_queues, config):
        super().__init__("EmailThread")
        self.msg_queues = msg_queues
        self.config = config

    def run(self):
        global check_email_delay

        check_email_delay = 60
        past = datetime.datetime.now()
        while not self.thread_stop:
            time.sleep(5)
            # always sleep for 5 seconds and see if we need to check email
            # This allows CTRL-C to stop the execution of this loop sooner
            # than check_email_delay time
            now = datetime.datetime.now()
            if now - past > datetime.timedelta(seconds=check_email_delay):
                # It's time to check email

                # slowly increase delay every iteration, max out at 300 seconds
                # any send/receive/resend activity will reset this to 60 seconds
                if check_email_delay < 300:
                    check_email_delay += 1
                LOG.debug("check_email_delay is " + str(check_email_delay) + " seconds")

                shortcuts = CONFIG["shortcuts"]
                # swap key/value
                shortcuts_inverted = {v: k for k, v in shortcuts.items()}

                date = datetime.datetime.now()
                month = date.strftime("%B")[:3]  # Nov, Mar, Apr
                day = date.day
                year = date.year
                today = "{}-{}-{}".format(day, month, year)

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
                        r"'([[A-a][0-9]_-]+@[[A-a][0-9]_-\.]+)",
                        str(envelope.from_[0]),
                    )
                    if f is not None:
                        from_addr = f.group(1)
                    else:
                        from_addr = "noaddr"

                    # LOG.debug("Message flags/tags:  " + str(server.get_flags(msgid)[msgid]))
                    # if "APRS" not in server.get_flags(msgid)[msgid]:
                    # in python3, imap tags are unicode.  in py2 they're strings. so .decode them to handle both
                    taglist = [
                        x.decode(errors="ignore")
                        for x in server.get_flags(msgid)[msgid]
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
                        # messaging.send_message(CONFIG["ham"]["callsign"], reply)
                        msg = messaging.TextMessage(
                            self.config["aprs"]["login"],
                            self.config["ham"]["callsign"],
                            reply,
                        )
                        self.msg_queues["tx"].put(msg)
                        # flag message as sent via aprs
                        server.add_flags(msgid, ["APRS"])
                        # unset seen flag, will stay bold in email client
                        server.remove_flags(msgid, [imapclient.SEEN])
                        # check email more often since we just received an email
                        check_email_delay = 60
                # reset clock
                past = datetime.datetime.now()
                server.logout()
            else:
                # We haven't hit the email delay yet.
                # LOG.debug("Delta({}) < {}".format(now - past, check_email_delay))
                pass

        # Remove ourselves from the global threads list
        threads.APRSDThreadList().remove(self)
        LOG.info("Exiting")


# end check_email()
