import datetime
import email
from email.mime.text import MIMEText
import imaplib
import logging
import re
import smtplib
import threading
import time

import imapclient
from validate_email import validate_email

from aprsd import messaging, plugin, stats, threads, trace


LOG = logging.getLogger("APRSD")


class EmailInfo:
    """A singleton thread safe mechanism for the global check_email_delay.

    This has to be done because we have 2 separate threads that access
    the delay value.
    1) when EmailPlugin runs from a user message and
    2) when the background EmailThread runs to check email.

    Access the check email delay with
    EmailInfo().delay

    Set it with
    EmailInfo().delay = 100
    or
    EmailInfo().delay += 10

    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.lock = threading.Lock()
            cls._instance._delay = 60
        return cls._instance

    @property
    def delay(self):
        with self.lock:
            return self._delay

    @delay.setter
    def delay(self, val):
        with self.lock:
            self._delay = val


class EmailPlugin(plugin.APRSDRegexCommandPluginBase):
    """Email Plugin."""

    command_regex = "^-.*"
    command_name = "email"
    short_description = "Send and Receive email"

    # message_number:time combos so we don't resend the same email in
    # five mins {int:int}
    email_sent_dict = {}
    enabled = False

    def setup(self):
        """Ensure that email is enabled and start the thread."""

        email_enabled = self.config["aprsd"]["email"].get("enabled", False)
        validation = self.config["aprsd"]["email"].get("validate", False)

        if email_enabled:
            valid = validate_email_config(self.config, validation)
            if not valid:
                LOG.error("Failed to validate email config options.")
                LOG.error("EmailPlugin DISABLED!!!!")
            else:
                self.enabled = True
        else:
            LOG.info("Email services not enabled.")

    def create_threads(self):
        if self.enabled:
            return APRSDEmailThread(
                msg_queues=threads.msg_queues,
                config=self.config,
            )

    @trace.trace
    def process(self, packet):
        LOG.info("Email COMMAND")
        if not self.enabled:
            # Email has not been enabled
            # so the plugin will just NOOP
            return messaging.NULL_MESSAGE

        fromcall = packet.get("from")
        message = packet.get("message_text", None)
        ack = packet.get("msgNo", "0")

        reply = None
        if not self.config["aprsd"]["email"].get("enabled", False):
            LOG.debug("Email is not enabled in config file ignoring.")
            return "Email not enabled."

        searchstring = "^" + self.config["ham"]["callsign"] + ".*"
        # only I can do email
        if re.search(searchstring, fromcall):
            # digits only, first one is number of emails to resend
            r = re.search("^-([0-9])[0-9]*$", message)
            if r is not None:
                LOG.debug("RESEND EMAIL")
                resend_email(self.config, r.group(1), fromcall)
                reply = messaging.NULL_MESSAGE
            # -user@address.com body of email
            elif re.search(r"^-([A-Za-z0-9_\-\.@]+) (.*)", message):
                # (same search again)
                a = re.search(r"^-([A-Za-z0-9_\-\.@]+) (.*)", message)
                if a is not None:
                    to_addr = a.group(1)
                    content = a.group(2)

                    email_address = get_email_from_shortcut(self.config, to_addr)
                    if not email_address:
                        reply = "Bad email address"
                        return reply

                    # send recipient link to aprs.fi map
                    if content == "mapme":
                        content = (
                            "Click for my location: http://aprs.fi/{}" ""
                        ).format(
                            self.config["ham"]["callsign"],
                        )
                    too_soon = 0
                    now = time.time()
                    # see if we sent this msg number recently
                    if ack in self.email_sent_dict:
                        # BUG(hemna) - when we get a 2 different email command
                        # with the same ack #, we don't send it.
                        timedelta = now - self.email_sent_dict[ack]
                        if timedelta < 300:  # five minutes
                            too_soon = 1
                    if not too_soon or ack == 0:
                        LOG.info(f"Send email '{content}'")
                        send_result = send_email(self.config, to_addr, content)
                        reply = messaging.NULL_MESSAGE
                        if send_result != 0:
                            reply = f"-{to_addr} failed"
                        else:
                            # clear email sent dictionary if somehow goes
                            # over 100
                            if len(self.email_sent_dict) > 98:
                                LOG.debug(
                                    "DEBUG: email_sent_dict is big ("
                                    + str(len(self.email_sent_dict))
                                    + ") clearing out.",
                                )
                                self.email_sent_dict.clear()
                            self.email_sent_dict[ack] = now
                    else:
                        reply = messaging.NULL_MESSAGE
                        LOG.info(
                            "Email for message number "
                            + ack
                            + " recently sent, not sending again.",
                        )
            else:
                reply = "Bad email address"
                # messaging.send_message(fromcall, "Bad email address")

        return reply


def _imap_connect(config):
    imap_port = config["aprsd"]["email"]["imap"].get("port", 143)
    use_ssl = config["aprsd"]["email"]["imap"].get("use_ssl", False)
    # host = CONFIG["aprsd"]["email"]["imap"]["host"]
    # msg = "{}{}:{}".format("TLS " if use_ssl else "", host, imap_port)
    #    LOG.debug("Connect to IMAP host {} with user '{}'".
    #              format(msg, CONFIG['imap']['login']))

    try:
        server = imapclient.IMAPClient(
            config["aprsd"]["email"]["imap"]["host"],
            port=imap_port,
            use_uid=True,
            ssl=use_ssl,
            timeout=30,
        )
    except Exception as e:
        LOG.error("Failed to connect IMAP server", e)
        return

    try:
        server.login(
            config["aprsd"]["email"]["imap"]["login"],
            config["aprsd"]["email"]["imap"]["password"],
        )
    except (imaplib.IMAP4.error, Exception) as e:
        msg = getattr(e, "message", repr(e))
        LOG.error(f"Failed to login {msg}")
        return

    server.select_folder("INBOX")

    server.fetch = trace.trace(server.fetch)
    server.search = trace.trace(server.search)
    server.remove_flags = trace.trace(server.remove_flags)
    server.add_flags = trace.trace(server.add_flags)
    return server


def _smtp_connect(config):
    host = config["aprsd"]["email"]["smtp"]["host"]
    smtp_port = config["aprsd"]["email"]["smtp"]["port"]
    use_ssl = config["aprsd"]["email"]["smtp"].get("use_ssl", False)
    msg = "{}{}:{}".format("SSL " if use_ssl else "", host, smtp_port)
    LOG.debug(
        "Connect to SMTP host {} with user '{}'".format(
            msg,
            config["aprsd"]["email"]["imap"]["login"],
        ),
    )

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(
                host=host,
                port=smtp_port,
                timeout=30,
            )
        else:
            server = smtplib.SMTP(
                host=host,
                port=smtp_port,
                timeout=30,
            )
    except Exception:
        LOG.error("Couldn't connect to SMTP Server")
        return

    LOG.debug(f"Connected to smtp host {msg}")

    debug = config["aprsd"]["email"]["smtp"].get("debug", False)
    if debug:
        server.set_debuglevel(5)
        server.sendmail = trace.trace(server.sendmail)

    try:
        server.login(
            config["aprsd"]["email"]["smtp"]["login"],
            config["aprsd"]["email"]["smtp"]["password"],
        )
    except Exception:
        LOG.error("Couldn't connect to SMTP Server")
        return

    LOG.debug(f"Logged into SMTP server {msg}")
    return server


def validate_shortcuts(config):
    shortcuts = config["aprsd"]["email"].get("shortcuts", None)
    if not shortcuts:
        return

    LOG.info(
        "Validating {} Email shortcuts. This can take up to 10 seconds"
        " per shortcut".format(len(shortcuts)),
    )
    delete_keys = []
    for key in shortcuts:
        LOG.info(f"Validating {key}:{shortcuts[key]}")
        is_valid = validate_email(
            email_address=shortcuts[key],
            check_format=True,
            check_dns=True,
            check_smtp=True,
            smtp_from_address=config["aprsd"]["email"]["smtp"]["login"],
            smtp_helo_host=config["aprsd"]["email"]["smtp"]["host"],
            smtp_timeout=10,
            dns_timeout=10,
            smtp_debug=False,
        )
        if not is_valid:
            LOG.error(
                "'{}' is an invalid email address. Removing shortcut".format(
                    shortcuts[key],
                ),
            )
            delete_keys.append(key)

    for key in delete_keys:
        del config["aprsd"]["email"]["shortcuts"][key]

    LOG.info(
        "Available shortcuts: {}".format(
            config["aprsd"]["email"]["shortcuts"],
        ),
    )


def get_email_from_shortcut(config, addr):
    if config["aprsd"]["email"].get("shortcuts", False):
        return config["aprsd"]["email"]["shortcuts"].get(addr, addr)
    else:
        return addr


def validate_email_config(config, disable_validation=False):
    """function to simply ensure we can connect to email services.

    This helps with failing early during startup.
    """
    LOG.info("Checking IMAP configuration")
    imap_server = _imap_connect(config)
    LOG.info("Checking SMTP configuration")
    smtp_server = _smtp_connect(config)

    # Now validate and flag any shortcuts as invalid
    if not disable_validation:
        validate_shortcuts(config)
    else:
        LOG.info("Shortcuts email validation is Disabled!!, you were warned.")

    if imap_server and smtp_server:
        return True
    else:
        return False


@trace.trace
def parse_email(msgid, data, server):
    envelope = data[b"ENVELOPE"]
    # email address match
    # use raw string to avoid invalid escape secquence errors r"string here"
    f = re.search(r"([\.\w_-]+@[\.\w_-]+)", str(envelope.from_[0]))
    if f is not None:
        from_addr = f.group(1)
    else:
        from_addr = "noaddr"
    LOG.debug(f"Got a message from '{from_addr}'")
    try:
        m = server.fetch([msgid], ["RFC822"])
    except Exception as e:
        LOG.exception("Couldn't fetch email from server in parse_email", e)
        return

    msg = email.message_from_string(m[msgid][b"RFC822"].decode(errors="ignore"))
    if msg.is_multipart():
        text = ""
        html = None
        # default in case body somehow isn't set below - happened once
        body = b"* unreadable msg received"
        # this uses the last text or html part in the email,
        # phone companies often put content in an attachment
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

    # FIXED:  UnicodeDecodeError: 'ascii' codec can't decode byte 0xf0
    # in position 6: ordinal not in range(128)
    # decode with errors='ignore'.   be sure to encode it before we return
    # it below, also with errors='ignore'
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
    return body, from_addr


# end parse_email


@trace.trace
def send_email(config, to_addr, content):
    shortcuts = config["aprsd"]["email"]["shortcuts"]
    email_address = get_email_from_shortcut(config, to_addr)
    LOG.info("Sending Email_________________")

    if to_addr in shortcuts:
        LOG.info("To          : " + to_addr)
        to_addr = email_address
        LOG.info(" (" + to_addr + ")")
    subject = config["ham"]["callsign"]
    # content = content + "\n\n(NOTE: reply with one line)"
    LOG.info("Subject     : " + subject)
    LOG.info("Body        : " + content)

    # check email more often since there's activity right now
    EmailInfo().delay = 60

    msg = MIMEText(content)
    msg["Subject"] = subject
    msg["From"] = config["aprsd"]["email"]["smtp"]["login"]
    msg["To"] = to_addr
    server = _smtp_connect(config)
    if server:
        try:
            server.sendmail(
                config["aprsd"]["email"]["smtp"]["login"],
                [to_addr],
                msg.as_string(),
            )
            stats.APRSDStats().email_tx_inc()
        except Exception as e:
            msg = getattr(e, "message", repr(e))
            LOG.error("Sendmail Error!!!! '{}'", msg)
            server.quit()
            return -1
        server.quit()
        return 0


@trace.trace
def resend_email(config, count, fromcall):
    date = datetime.datetime.now()
    month = date.strftime("%B")[:3]  # Nov, Mar, Apr
    day = date.day
    year = date.year
    today = f"{day}-{month}-{year}"

    shortcuts = config["aprsd"]["email"]["shortcuts"]
    # swap key/value
    shortcuts_inverted = {v: k for k, v in shortcuts.items()}

    try:
        server = _imap_connect(config)
    except Exception as e:
        LOG.exception("Failed to Connect to IMAP. Cannot resend email ", e)
        return

    try:
        messages = server.search(["SINCE", today])
    except Exception as e:
        LOG.exception("Couldn't search for emails in resend_email ", e)
        return

    # LOG.debug("%d messages received today" % len(messages))

    msgexists = False

    messages.sort(reverse=True)
    del messages[int(count) :]  # only the latest "count" messages
    for message in messages:
        try:
            parts = server.fetch(message, ["ENVELOPE"]).items()
        except Exception as e:
            LOG.exception("Couldn't fetch email parts in resend_email", e)
            continue

        for msgid, data in list(parts):
            # one at a time, otherwise order is random
            (body, from_addr) = parse_email(msgid, data, server)
            # unset seen flag, will stay bold in email client
            try:
                server.remove_flags(msgid, [imapclient.SEEN])
            except Exception as e:
                LOG.exception("Failed to remove SEEN flag in resend_email", e)

            if from_addr in shortcuts_inverted:
                # reverse lookup of a shortcut
                from_addr = shortcuts_inverted[from_addr]
            # asterisk indicates a resend
            reply = "-" + from_addr + " * " + body.decode(errors="ignore")
            # messaging.send_message(fromcall, reply)
            msg = messaging.TextMessage(
                config["aprs"]["login"],
                fromcall,
                reply,
            )
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
        msg = messaging.TextMessage(config["aprs"]["login"], fromcall, reply)
        msg.send()

    # check email more often since we're resending one now
    EmailInfo().delay = 60

    server.logout()
    # end resend_email()


class APRSDEmailThread(threads.APRSDThread):
    def __init__(self, msg_queues, config):
        super().__init__("EmailThread")
        self.msg_queues = msg_queues
        self.config = config
        self.past = datetime.datetime.now()

    def loop(self):
        time.sleep(5)
        stats.APRSDStats().email_thread_update()
        # always sleep for 5 seconds and see if we need to check email
        # This allows CTRL-C to stop the execution of this loop sooner
        # than check_email_delay time
        now = datetime.datetime.now()
        if now - self.past > datetime.timedelta(seconds=EmailInfo().delay):
            # It's time to check email

            # slowly increase delay every iteration, max out at 300 seconds
            # any send/receive/resend activity will reset this to 60 seconds
            if EmailInfo().delay < 300:
                EmailInfo().delay += 10
            LOG.debug(
                f"check_email_delay is {EmailInfo().delay} seconds ",
            )

            shortcuts = self.config["aprsd"]["email"]["shortcuts"]
            # swap key/value
            shortcuts_inverted = {v: k for k, v in shortcuts.items()}

            date = datetime.datetime.now()
            month = date.strftime("%B")[:3]  # Nov, Mar, Apr
            day = date.day
            year = date.year
            today = f"{day}-{month}-{year}"

            try:
                server = _imap_connect(self.config)
            except Exception as e:
                LOG.exception("IMAP failed to connect.", e)
                return True

            try:
                messages = server.search(["SINCE", today])
            except Exception as e:
                LOG.exception(
                    "IMAP failed to search for messages since today.",
                    e,
                )
                return True
            LOG.debug(f"{len(messages)} messages received today")

            try:
                _msgs = server.fetch(messages, ["ENVELOPE"])
            except Exception as e:
                LOG.exception("IMAP failed to fetch/flag messages: ", e)
                return True

            for msgid, data in _msgs.items():
                envelope = data[b"ENVELOPE"]
                LOG.debug(
                    'ID:%d  "%s" (%s)'
                    % (msgid, envelope.subject.decode(), envelope.date),
                )
                f = re.search(
                    r"'([[A-a][0-9]_-]+@[[A-a][0-9]_-\.]+)",
                    str(envelope.from_[0]),
                )
                if f is not None:
                    from_addr = f.group(1)
                else:
                    from_addr = "noaddr"

                # LOG.debug("Message flags/tags:  " +
                # str(server.get_flags(msgid)[msgid]))
                # if "APRS" not in server.get_flags(msgid)[msgid]:
                # in python3, imap tags are unicode.  in py2 they're strings.
                # so .decode them to handle both
                try:
                    taglist = [
                        x.decode(errors="ignore")
                        for x in server.get_flags(msgid)[msgid]
                    ]
                except Exception as e:
                    LOG.exception("Failed to get flags.", e)
                    break

                if "APRS" not in taglist:
                    # if msg not flagged as sent via aprs
                    try:
                        server.fetch([msgid], ["RFC822"])
                    except Exception as e:
                        LOG.exception(
                            "Failed single server fetch for RFC822",
                            e,
                        )
                        break

                    (body, from_addr) = parse_email(msgid, data, server)
                    # unset seen flag, will stay bold in email client
                    try:
                        server.remove_flags(msgid, [imapclient.SEEN])
                    except Exception as e:
                        LOG.exception("Failed to remove flags SEEN", e)
                        # Not much we can do here, so lets try and
                        # send the aprs message anyway

                    if from_addr in shortcuts_inverted:
                        # reverse lookup of a shortcut
                        from_addr = shortcuts_inverted[from_addr]

                    reply = "-" + from_addr + " " + body.decode(errors="ignore")
                    msg = messaging.TextMessage(
                        self.config["aprs"]["login"],
                        self.config["ham"]["callsign"],
                        reply,
                    )
                    msg.send()
                    # flag message as sent via aprs
                    try:
                        server.add_flags(msgid, ["APRS"])
                        # unset seen flag, will stay bold in email client
                    except Exception as e:
                        LOG.exception("Couldn't add APRS flag to email", e)

                    try:
                        server.remove_flags(msgid, [imapclient.SEEN])
                    except Exception as e:
                        LOG.exception("Couldn't remove seen flag from email", e)

                    # check email more often since we just received an email
                    EmailInfo().delay = 60

            # reset clock
            LOG.debug("Done looping over Server.fetch, logging out.")
            self.past = datetime.datetime.now()
            try:
                server.logout()
            except Exception as e:
                LOG.exception("IMAP failed to logout: ", e)
                return True
        else:
            # We haven't hit the email delay yet.
            # LOG.debug("Delta({}) < {}".format(now - past, check_email_delay))
            return True

        return True
