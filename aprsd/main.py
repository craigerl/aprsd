# -*- coding: utf-8 -*-
#
# Listen on amateur radio aprs-is network for messages and respond to them.
# You must have an amateur radio callsign to use this software.  You must
# create an ~/.aprsd/config.yml file with all of the required settings.  To
# generate an example config.yml, just run aprsd, then copy the sample config
# to ~/.aprsd/config.yml and edit the settings.
#
# APRS messages:
#   l(ocation)             = descriptive location of calling station
#   w(eather)              = temp, (hi/low) forecast, later forecast
#   t(ime)                 = respond with the current time
#   f(ortune)              = respond with a short fortune
#   -email_addr email text = send an email
#   -2                     = display the last 2 emails received
#   p(ing)                 = respond with Pong!/time
#   anything else          = respond with usage
#
# (C)2018 Craig Lamparter
# License GPLv2
#

# python included libs
import datetime
import email
import imaplib
import logging
import os
import pprint
import re
import select
import signal
import smtplib
import socket
import sys
import threading
import time
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler

import click
import click_completion
import imapclient
import six
import yaml

# local imports here
import aprsd
from aprsd import plugin, utils

# setup the global logger
LOG = logging.getLogger("APRSD")

# global for the config yaml
CONFIG = None

# localization, please edit:
# HOST = "noam.aprs2.net"     # north america tier2 servers round robin
# USER = "KM6XXX-9"           # callsign of this aprs client with SSID
# PASS = "99999"              # google how to generate this
# BASECALLSIGN = "KM6XXX"     # callsign of radio in the field to send email
# shortcuts = {
#   "aa" : "5551239999@vtext.com",
#   "cl" : "craiglamparter@somedomain.org",
#   "wb" : "5553909472@vtext.com"
# }

# globals - tell me a better way to update data being used by threads

# message_number:time combos so we don't resend the same email in
# five mins {int:int}
email_sent_dict = {}

# message_nubmer:ack  combos so we stop sending a message after an
# ack from radio {int:int}
ack_dict = {}

# current aprs radio message number, increments for each message we
# send over rf {int}
message_number = 0

# global telnet connection object -- not needed anymore
# tn = None

# ## set default encoding for python, so body.decode doesn't blow up in email thread
# reload(sys)
# sys.setdefaultencoding('utf8')

# import locale
# def getpreferredencoding(do_setlocale = True):
#   return "utf-8"
# locale.getpreferredencoding = getpreferredencoding
# ## default encoding failed attempts....


def custom_startswith(string, incomplete):
    """A custom completion match that supports case insensitive matching."""
    if os.environ.get("_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE"):
        string = string.lower()
        incomplete = incomplete.lower()
    return string.startswith(incomplete)


click_completion.core.startswith = custom_startswith
click_completion.init()


cmd_help = """Shell completion for click-completion-command
Available shell types:
\b
  %s
Default type: auto
""" % "\n  ".join(
    "{:<12} {}".format(k, click_completion.core.shells[k])
    for k in sorted(click_completion.core.shells.keys())
)


@click.group(help=cmd_help)
@click.version_option()
def main():
    pass


@main.command()
@click.option(
    "-i", "--case-insensitive/--no-case-insensitive", help="Case insensitive completion"
)
@click.argument(
    "shell",
    required=False,
    type=click_completion.DocumentedChoice(click_completion.core.shells),
)
def show(shell, case_insensitive):
    """Show the click-completion-command completion code"""
    extra_env = (
        {"_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE": "ON"}
        if case_insensitive
        else {}
    )
    click.echo(click_completion.core.get_code(shell, extra_env=extra_env))


@main.command()
@click.option(
    "--append/--overwrite", help="Append the completion code to the file", default=None
)
@click.option(
    "-i", "--case-insensitive/--no-case-insensitive", help="Case insensitive completion"
)
@click.argument(
    "shell",
    required=False,
    type=click_completion.DocumentedChoice(click_completion.core.shells),
)
@click.argument("path", required=False)
def install(append, case_insensitive, shell, path):
    """Install the click-completion-command completion"""
    extra_env = (
        {"_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE": "ON"}
        if case_insensitive
        else {}
    )
    shell, path = click_completion.core.install(
        shell=shell, path=path, append=append, extra_env=extra_env
    )
    click.echo("%s completion installed in %s" % (shell, path))


def setup_connection():
    global sock
    connected = False
    while not connected:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(300)
            sock.connect((CONFIG["aprs"]["host"], 14580))
            connected = True
            LOG.debug("Connected to server: " + CONFIG["aprs"]["host"])
            # sock_file = sock.makefile(mode="r")
            # sock_file = sock.makefile(mode='r',  encoding=None, errors=None, newline=None)
            # sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # disable nagle algorithm
            # sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 512)  # buffer size
        except Exception as e:
            LOG.error("Unable to connect to APRS-IS server.\n")
            print(str(e))
            time.sleep(5)
            continue
            # os._exit(1)
    user = CONFIG["aprs"]["login"]
    password = CONFIG["aprs"]["password"]
    LOG.debug("Logging in to APRS-IS with user '%s'" % user)
    msg = "user {} pass {} vers aprsd {}\n".format(user, password, aprsd.__version__)
    sock.send(msg.encode())
    return sock


def signal_handler(signal, frame):
    LOG.info("Ctrl+C, exiting.")
    # sys.exit(0)  # thread ignores this
    os._exit(0)


# end signal_handler


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
        body = "* unreadable msg received"
        # this uses the last text or html part in the email, phone companies often put content in an attachment
        for part in msg.get_payload():
            if (
                part.get_content_charset() is None
            ):  # or BREAK when we hit a text or html?
                # We cannot know the character set,
                # so return decoded "something"
                text = part.get_payload(decode=True)
                continue

            charset = part.get_content_charset()

            if part.get_content_type() == "text/plain":
                text = six.text_type(
                    part.get_payload(decode=True), str(charset), "ignore"
                ).encode("utf8", "replace")

            if part.get_content_type() == "text/html":
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

    #    LOG.debug("Connected to IMAP host {}".format(msg))

    try:
        server.login(CONFIG["imap"]["login"], CONFIG["imap"]["password"])
    except (imaplib.IMAP4.error, Exception) as e:
        msg = getattr(e, "message", repr(e))
        LOG.error("Failed to login {}".format(msg))
        return

    #    LOG.debug("Logged in to IMAP, selecting INBOX")
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
            send_message(fromcall, reply)
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
        send_message(fromcall, reply)

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
                send_message(CONFIG["ham"]["callsign"], reply)
                # flag message as sent via aprs
                server.add_flags(msgid, ["APRS"])
                # unset seen flag, will stay bold in email client
                server.remove_flags(msgid, [imapclient.SEEN])
                # check email more often since we just received an email
                check_email_delay = 60

        server.logout()


# end check_email()


def send_ack_thread(tocall, ack, retry_count):
    tocall = tocall.ljust(9)  # pad to nine chars
    line = "{}>APRS::{}:ack{}\n".format(CONFIG["aprs"]["login"], tocall, ack)
    for i in range(retry_count, 0, -1):
        LOG.info("Sending ack __________________ Tx({})".format(i))
        LOG.info("Raw         : {}".format(line.rstrip("\n")))
        LOG.info("To          : {}".format(tocall))
        LOG.info("Ack number  : {}".format(ack))
        sock.send(line.encode())
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
    global ack_dict
    # line = (CONFIG['aprs']['login'] + ">APRS::" + tocall + ":" + message
    #        + "{" + str(this_message_number) + "\n")
    # line = ("{}>APRS::{}:{}{{{}\n".format( CONFIG['aprs']['login'], tocall, message.encode(errors='ignore'), str(this_message_number),))
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
            sock.send(line.encode())
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


# Setup the logging faciility
# to disable logging to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(loglevel, quiet):
    levels = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
    }
    log_level = levels[loglevel]

    LOG.setLevel(log_level)
    log_format = "%(asctime)s [%(threadName)-12s] [%(levelname)-5.5s]" " %(message)s"
    date_format = "%m/%d/%Y %I:%M:%S %p"
    log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    fh = RotatingFileHandler(
        CONFIG["aprs"]["logfile"], maxBytes=(10248576 * 5), backupCount=4
    )
    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    if not quiet:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        LOG.addHandler(sh)


@main.command()
def sample_config():
    """This dumps the config to stdout."""
    click.echo(yaml.dump(utils.DEFAULT_CONFIG_DICT))


COMMAND_ENVELOPE = {
    "email": {"command": "^-.*", "function": "command_email"},
}


def command_email(fromcall, message, ack):
    LOG.info("Email COMMAND")

    searchstring = "^" + CONFIG["ham"]["callsign"] + ".*"
    # only I can do email
    if re.search(searchstring, fromcall):
        # digits only, first one is number of emails to resend
        r = re.search("^-([0-9])[0-9]*$", message)
        if r is not None:
            resend_email(r.group(1), fromcall)
        # -user@address.com body of email
        elif re.search(r"^-([A-Za-z0-9_\-\.@]+) (.*)", message):
            # (same search again)
            a = re.search(r"^-([A-Za-z0-9_\-\.@]+) (.*)", message)
            if a is not None:
                to_addr = a.group(1)
                content = a.group(2)
                # send recipient link to aprs.fi map
                if content == "mapme":
                    content = "Click for my location: http://aprs.fi/{}".format(
                        CONFIG["ham"]["callsign"]
                    )
                too_soon = 0
                now = time.time()
                # see if we sent this msg number recently
                if ack in email_sent_dict:
                    timedelta = now - email_sent_dict[ack]
                    if timedelta < 300:  # five minutes
                        too_soon = 1
                if not too_soon or ack == 0:
                    send_result = send_email(to_addr, content)
                    if send_result != 0:
                        send_message(fromcall, "-" + to_addr + " failed")
                    else:
                        # send_message(fromcall, "-" + to_addr + " sent")
                        if (
                            len(email_sent_dict) > 98
                        ):  # clear email sent dictionary if somehow goes over 100
                            LOG.debug(
                                "DEBUG: email_sent_dict is big ("
                                + str(len(email_sent_dict))
                                + ") clearing out."
                            )
                            email_sent_dict.clear()
                        email_sent_dict[ack] = now
                else:
                    LOG.info(
                        "Email for message number "
                        + ack
                        + " recently sent, not sending again."
                    )
        else:
            send_message(fromcall, "Bad email address")

    return (fromcall, message, ack)


# main() ###
@main.command()
@click.option(
    "--loglevel",
    default="DEBUG",
    show_default=True,
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], case_sensitive=False
    ),
    show_choices=True,
    help="The log level to use for aprsd.log",
)
@click.option("--quiet", is_flag=True, default=False, help="Don't log to stdout")
@click.option(
    "-c",
    "--config",
    "config_file",
    show_default=True,
    default=utils.DEFAULT_CONFIG_FILE,
    help="The aprsd config file to use for options.",
)
def server(loglevel, quiet, config_file):
    """Start the aprsd server process."""
    global CONFIG

    CONFIG = utils.parse_config(config_file)
    signal.signal(signal.SIGINT, signal_handler)
    setup_logging(loglevel, quiet)
    LOG.info("APRSD Started version: {}".format(aprsd.__version__))

    time.sleep(2)
    client_sock = setup_connection()
    valid = validate_email()
    if not valid:
        LOG.error("Failed to validate email config options")
        sys.exit(-1)

    user = CONFIG["aprs"]["login"]
    LOG.debug("Looking for messages for user '{}'".format(user))
    # password = CONFIG["aprs"]["password"]
    # LOG.debug("LOGIN to APRSD with user '%s'" % user)
    # msg = ("user {} pass {} vers aprsd {}\n".format(user, password, aprsd.__version__))
    # sock.send(msg.encode())

    time.sleep(2)

    checkemailthread = threading.Thread(
        target=check_email_thread, name="check_email", args=()
    )  # args must be tuple
    checkemailthread.start()

    read_sockets = [client_sock]

    # Register plugins
    pm = plugin.setup_plugins(CONFIG)

    fromcall = message = ack = None
    while True:
        LOG.debug("Main loop start")
        reconnect = False
        message = None
        try:
            readable, writable, exceptional = select.select(read_sockets, [], [])

            for s in readable:
                data = s.recv(10240).decode().strip()
                if data:
                    LOG.info("APRS-IS({}): {}".format(len(data), data))
                    searchstring = "::%s" % user
                    if re.search(searchstring, data):
                        LOG.debug(
                            "main: found message addressed to us begin process_message"
                        )
                        (fromcall, message, ack) = process_message(data)
                else:
                    LOG.error("Connection Failed. retrying to connect")
                    read_sockets.remove(s)
                    s.close()
                    time.sleep(2)
                    client_sock = setup_connection()
                    read_sockets.append(client_sock)
                    reconnect = True

            for s in exceptional:
                LOG.error("Connection Failed. retrying to connect")
                read_sockets.remove(s)
                s.close()
                time.sleep(2)
                client_sock = setup_connection()
                read_sockets.append(client_sock)
                reconnect = True

            if reconnect:
                # start the loop over
                LOG.warning("Starting Main loop over.")
                continue

        except Exception as e:
            LOG.exception(e)
            LOG.error("%s" % str(e))
            if (
                str(e) == "closed_socket"
                or str(e) == "timed out"
                or str(e) == "Temporary failure in name resolution"
                or str(e) == "Network is unreachable"
            ):
                LOG.error("Attempting to reconnect.")
                sock.shutdown(0)
                sock.close()
                client_sock = setup_connection()
                continue
            LOG.error("Unexpected error: " + str(e))
            LOG.error("Continuing anyway.")
            time.sleep(5)
            continue  # don't know what failed, so wait and then continue main loop again

        if not message:
            continue

        LOG.debug("Process the command. '{}'".format(message))

        # ACK (ack##)
        # Custom command due to needing to avoid send_ack
        if re.search("^ack[0-9]+", message):
            LOG.debug("ACK")
            # put message_number:1 in dict to record the ack
            a = re.search("^ack([0-9]+)", message)
            ack_dict.update({int(a.group(1)): 1})
            continue  # break out of this so we don't ack an ack at the end

        # call our `myhook` hook
        found_command = False
        results = pm.hook.run(fromcall=fromcall, message=message, ack=ack)
        for reply in results:
            found_command = True
            send_message(fromcall, reply)

        # it's not an ack, so try and process user input
        for key in COMMAND_ENVELOPE:
            if re.search(COMMAND_ENVELOPE[key]["command"], message):
                # now call the registered function
                funct = COMMAND_ENVELOPE[key]["function"]
                (fromcall, message, ack) = globals()[funct](fromcall, message, ack)
                found_command = True

        if not found_command:
            plugins = pm.get_plugins()
            names = [x.command_name for x in plugins]
            for k in COMMAND_ENVELOPE.keys():
                names.append(k)
            names.sort()

            reply = "Usage: {}".format(", ".join(names))
            send_message(fromcall, reply)

        # let any threads do their thing, then ack
        time.sleep(1)
        # send an ack last
        send_ack(fromcall, ack)
        LOG.debug("Main loop end")
    # end while True


if __name__ == "__main__":
    main()
