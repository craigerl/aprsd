#!/usr/bin/python -u
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
import argparse
import datetime
import email
import json
import logging
import os
import socket
import pprint
import re
import signal
import six
import smtplib
import subprocess
import sys
# import telnetlib
import threading
import time
import urllib

from email.mime.text import MIMEText
import imapclient
import imaplib
from logging.handlers import RotatingFileHandler

# local imports here
import aprsd
from aprsd.fuzzyclock import fuzzy
from aprsd import utils

# setup the global logger
LOG = logging.getLogger('APRSD')

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
tn = None

# command line args
parser = argparse.ArgumentParser()
parser.add_argument("--loglevel",
                    default='DEBUG',
                    choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                    help="The log level to use for aprsd.log")
parser.add_argument("--quiet",
                    action='store_true',
                    help="Don't log to stdout")

args = parser.parse_args()


# def setup_connection():
#    global tn
#    host = CONFIG['aprs']['host']
#    port = CONFIG['aprs']['port']
#    LOG.debug("Setting up telnet connection to '%s:%s'" % (host, port))
#    try:
#        tn = telnetlib.Telnet(host, port)
#    except Exception:
#        LOG.exception("Telnet session failed.")
#        sys.exit(-1)

def setup_connection():
    global sock
    global sock_file
    connected = False
    while not connected:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((CONFIG['aprs']['host'], 14580))
            sock.settimeout(60)
            connected = True
        except Exception as e:
            print("Unable to connect to APRS-IS server.\n")
            print(str(e))
            time.sleep(5)
            continue
            # os._exit(1)
        sock_file = sock.makefile(mode='r')
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # disable nagle algorithm
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 512)  # buffer size


def signal_handler(signal, frame):
    LOG.info("Ctrl+C, exiting.")
    # sys.exit(0)  # thread ignores this
    os._exit(0)


# end signal_handler
def parse_email(msgid, data, server):
    envelope = data[b'ENVELOPE']
    # email address match
    # use raw string to avoid invalid escape secquence errors r"string here"
    f = re.search(r"([\.\w_-]+@[\.\w_-]+)", str(envelope.from_[0]))
    if f is not None:
        from_addr = f.group(1)
    else:
        from_addr = "noaddr"
    LOG.debug("Got a message from '{}'".format(from_addr))
    m = server.fetch([msgid], ['RFC822'])
    msg = email.message_from_string(m[msgid][b'RFC822'].decode())
    if msg.is_multipart():
        text = ""
        html = None
        # default in case body somehow isn't set below - happened once
        body = "* unreadable msg received"
        for part in msg.get_payload():
            if part.get_content_charset() is None:
                # We cannot know the character set,
                # so return decoded "something"
                text = part.get_payload(decode=True)
                continue

            charset = part.get_content_charset()

            if part.get_content_type() == 'text/plain':
                text = six.text_type(
                    part.get_payload(decode=True), str(charset),
                    "ignore").encode('utf8', 'replace')

            if part.get_content_type() == 'text/html':
                html = six.text_type(
                    part.get_payload(decode=True),
                    str(charset),
                    "ignore").encode('utf8', 'replace')

            if text is not None:
                # strip removes white space fore and aft of string
                body = text.strip()
            else:
                body = html.strip()
    else:
        # email.uscc.net sends no charset, blows up unicode function below
        if msg.get_content_charset() is None:
            text = six.text_type(
                msg.get_payload(decode=True),
                'US-ASCII',
                'ignore').encode('utf8', 'replace')
        else:
            text = six.text_type(
                msg.get_payload(decode=True),
                msg.get_content_charset(),
                'ignore').encode('utf8', 'replace')
        body = text.strip()

    # strip all html tags
    body = body.decode()
    body = re.sub('<[^<]+?>', '', body)
    # strip CR/LF, make it one line, .rstrip fails at this
    body = body.replace("\n", " ").replace("\r", " ")
    return(body, from_addr)
# end parse_email


def _imap_connect():
    imap_port = CONFIG['imap'].get('port', 143)
    use_ssl = CONFIG['imap'].get('use_ssl', False)
    host = CONFIG['imap']['host']
    msg = ("{}{}:{}".format(
        'TLS ' if use_ssl else '',
        host,
        imap_port
    ))
    LOG.debug("Connect to IMAP host {} with user '{}'".
              format(msg, CONFIG['imap']['login']))

    try:
        server = imapclient.IMAPClient(CONFIG['imap']['host'], port=imap_port,
                                       use_uid=True, ssl=use_ssl)
    except Exception:
        LOG.error("Failed to connect IMAP server")
        return

    LOG.debug("Connected to IMAP host {}".format(msg))

    try:
        server.login(CONFIG['imap']['login'], CONFIG['imap']['password'])
    except (imaplib.IMAP4.error, Exception) as e:
        msg = getattr(e, 'message', repr(e))
        LOG.error("Failed to login {}".format(msg))
        return

    LOG.debug("Logged in to IMAP, selecting INBOX")
    server.select_folder('INBOX')
    return server


def _smtp_connect():
    host = CONFIG['smtp']['host']
    smtp_port = CONFIG['smtp']['port']
    use_ssl = CONFIG['smtp'].get('use_ssl', False)
    msg = ("{}{}:{}".format(
        'SSL ' if use_ssl else '',
        host,
        smtp_port
    ))
    LOG.debug("Connect to SMTP host {} with user '{}'".
              format(msg, CONFIG['imap']['login']))

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
        server.login(CONFIG['smtp']['login'], CONFIG['smtp']['password'])
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
    date = datetime.datetime.now()
    month = date.strftime("%B")[:3]       # Nov, Mar, Apr
    day = date.day
    year = date.year
    today = "%s-%s-%s" % (day, month, year)

    shortcuts = CONFIG['shortcuts']
    # swap key/value
    shortcuts_inverted = dict([[v, k] for k, v in shortcuts.items()])

    try:
        server = _imap_connect()
    except Exception as e:
        LOG.exception("Failed to Connect to IMAP. Cannot resend email ", e)
        return

    messages = server.search(['SINCE', today])
    LOG.debug("%d messages received today" % len(messages))

    msgexists = False

    messages.sort(reverse=True)
    del messages[int(count):]          # only the latest "count" messages
    for message in messages:
        for msgid, data in list(server.fetch(message, ['ENVELOPE']).items()):
            # one at a time, otherwise order is random
            (body, from_addr) = parse_email(msgid, data, server)
            # unset seen flag, will stay bold in email client
            server.remove_flags(msgid, [imapclient.SEEN])
            if from_addr in shortcuts_inverted:
                # reverse lookup of a shortcut
                from_addr = shortcuts_inverted[from_addr]
            # asterisk indicates a resend
            reply = "-" + from_addr + " * " + body
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
        reply = "No new msg %s:%s:%s" % (str(h).zfill(2),
                                         str(m).zfill(2),
                                         str(s).zfill(2))
        send_message(fromcall, reply)

    server.logout()
    # end resend_email()


def check_email_thread(check_email_delay):

    while True:
        # threading.Timer(55, check_email_thread).start()
        LOG.debug("Top of check_email_thread.")

        time.sleep(check_email_delay)

        shortcuts = CONFIG['shortcuts']
        # swap key/value
        shortcuts_inverted = dict([[v, k] for k, v in shortcuts.items()])

        date = datetime.datetime.now()
        month = date.strftime("%B")[:3]       # Nov, Mar, Apr
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

        messages = server.search(['SINCE', today])
        LOG.debug("{} messages received today".format(len(messages)))

        for msgid, data in server.fetch(messages, ['ENVELOPE']).items():
            envelope = data[b'ENVELOPE']
            LOG.debug('ID:%d  "%s" (%s)' %
                      (msgid, envelope.subject.decode(), envelope.date))
            f = re.search(r"'([[A-a][0-9]_-]+@[[A-a][0-9]_-\.]+)",
                          str(envelope.from_[0]))
            if f is not None:
                from_addr = f.group(1)
            else:
                from_addr = "noaddr"

            if "APRS" not in server.get_flags(msgid)[msgid]:
                # if msg not flagged as sent via aprs
                server.fetch([msgid], ['RFC822'])
                (body, from_addr) = parse_email(msgid, data, server)
                # unset seen flag, will stay bold in email client
                server.remove_flags(msgid, [imapclient.SEEN])

                if from_addr in shortcuts_inverted:
                    # reverse lookup of a shortcut
                    from_addr = shortcuts_inverted[from_addr]

                reply = "-" + from_addr + " " + body
                # print "Sending message via aprs: " + reply
                # radio
                send_message(CONFIG['ham']['callsign'], reply)
                # flag message as sent via aprs
                server.add_flags(msgid, ['APRS'])
                # unset seen flag, will stay bold in email client
                server.remove_flags(msgid, [imapclient.SEEN])

        server.logout()

# end check_email()


def send_ack_thread(tocall, ack, retry_count):
    tocall = tocall.ljust(9)  # pad to nine chars
    line = ("{}>APRS::{}:ack{}\n".format(
        CONFIG['aprs']['login'], tocall, ack))
    for i in range(retry_count, 0, -1):
        LOG.info("Sending ack __________________ Tx({})".format(i))
        LOG.info("Raw         : {}".format(line))
        LOG.info("To          : {}".format(tocall))
        LOG.info("Ack number  : {}".format(ack))
        # tn.write(line)
        sock.send(line.encode())
        # aprs duplicate detection is 30 secs?
        # (21 only sends first, 28 skips middle)
        time.sleep(31)
    return()
    # end_send_ack_thread


def send_ack(tocall, ack):
    retry_count = 3
    thread = threading.Thread(target=send_ack_thread,
                              name="send_ack",
                              args=(tocall, ack, retry_count))
    thread.start()
    return()
    # end send_ack()


def send_message_thread(tocall, message, this_message_number, retry_count):
    global ack_dict
    # line = (CONFIG['aprs']['login'] + ">APRS::" + tocall + ":" + message
    #        + "{" + str(this_message_number) + "\n")
    line = ("{}>APRS::{}:{}{{{}\n".format(
        CONFIG['aprs']['login'],
        tocall, message,
        str(this_message_number),
    ))
    for i in range(retry_count, 0, -1):
        LOG.debug("DEBUG: send_message_thread msg:ack combos are: ")
        LOG.debug(pprint.pformat(ack_dict))
        if ack_dict[this_message_number] != 1:
            LOG.info("Sending message_______________ {}(Tx{})"
                     .format(
                         str(this_message_number),
                         str(i)
                     ))
            LOG.info("Raw         : {}".format(line))
            LOG.info("To          : {}".format(tocall))
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
    if message_number > 98:        # global
        message_number = 0
    message_number += 1
    if len(ack_dict) > 90:
        # empty ack dict if it's really big, could result in key error later
        LOG.debug("DEBUG: Length of ack dictionary is big at %s clearing." %
                  len(ack_dict))
        ack_dict.clear()
        LOG.debug(pprint.pformat(ack_dict))
        LOG.debug("DEBUG: Cleared ack dictionary, ack_dict length is now %s." %
                  len(ack_dict))
    ack_dict[message_number] = 0   # clear ack for this message number
    tocall = tocall.ljust(9)    # pad to nine chars

    # max?  ftm400 displays 64, raw msg shows 74
    # and ftm400-send is max 64.  setting this to
    # 67 displays 64 on the ftm400. (+3 {01 suffix)
    # feature req: break long ones into two msgs
    message = message[:67]
    thread = threading.Thread(
        target=send_message_thread,
        name="send_message",
        args=(tocall, message, message_number, retry_count))
    thread.start()
    return()
    # end send_message()


def process_message(line):
    f = re.search('^(.*)>', line)
    fromcall = f.group(1)
    searchstring = '::%s[ ]*:(.*)' % CONFIG['aprs']['login']
    # verify this, callsign is padded out with spaces to colon
    m = re.search(searchstring, line)
    fullmessage = m.group(1)

    ack_attached = re.search('(.*){([0-9A-Z]+)', fullmessage)
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
    LOG.info("Sending Email_________________")
    shortcuts = CONFIG['shortcuts']
    if to_addr in shortcuts:
        LOG.info("To          : " + to_addr)
        to_addr = shortcuts[to_addr]
        LOG.info(" (" + to_addr + ")")
    subject = CONFIG['ham']['callsign']
    # content = content + "\n\n(NOTE: reply with one line)"
    LOG.info("Subject     : " + subject)
    LOG.info("Body        : " + content)

    msg = MIMEText(content)
    msg['Subject'] = subject
    msg['From'] = CONFIG['smtp']['login']
    msg['To'] = to_addr
    server = _smtp_connect()
    if server:
        try:
            server.sendmail(CONFIG['smtp']['login'], [to_addr], msg.as_string())
        except Exception as e:
            msg = getattr(e, 'message', repr(e))
            LOG.error("Sendmail Error!!!! '{}'", msg)
            server.quit()
            return(-1)
        server.quit()
        return(0)
    # end send_email


# Setup the logging faciility
# to disable logging to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(args):
    global LOG
    levels = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG}
    log_level = levels[args.loglevel]

    LOG.setLevel(log_level)
    log_format = ("%(asctime)s [%(threadName)-12s] [%(levelname)-5.5s]"
                  " %(message)s")
    date_format = '%m/%d/%Y %I:%M:%S %p'
    log_formatter = logging.Formatter(fmt=log_format,
                                      datefmt=date_format)
    fh = RotatingFileHandler(CONFIG['aprs']['logfile'],
                             maxBytes=(10248576 * 5),
                             backupCount=4)
    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    if not args.quiet:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        LOG.addHandler(sh)


# main() ###
def main(args=args):
    global CONFIG

    CONFIG = utils.parse_config(args)
    signal.signal(signal.SIGINT, signal_handler)
    setup_logging(args)
    LOG.info("APRSD Started version: {}".format(aprsd.__version__))

    time.sleep(2)
    setup_connection()
    valid = validate_email()
    if not valid:
        LOG.error("Failed to validate email config options")
        sys.exit(-1)

    user = CONFIG['aprs']['login']
    password = CONFIG['aprs']['password']
    LOG.debug("LOGIN to APRSD with user '%s'" % user)
    msg = ("user {} pass {} vers aprsd {}\n".format(user, password,
                                                    aprsd.__version__))
    sock.send(msg.encode())

    time.sleep(2)

    check_email_delay = 60  # initial email check interval
    checkemailthread = threading.Thread(target=check_email_thread,
                                        name="check_email",
                                        args=(check_email_delay, ))  # args must be tuple
    checkemailthread.start()

    LOG.info("Start main loop")
    while True:
        line = ""
        try:
            line = sock_file.readline().strip()
            if line:
                LOG.info(line)
            searchstring = '::%s' % user
            # is aprs message to us, not beacon, status, etc
            if re.search(searchstring, line):
                (fromcall, message, ack) = process_message(line)
            else:
                message = "noise"
                continue

            # ACK (ack##)
            if re.search('^ack[0-9]+', message):
                # put message_number:1 in dict to record the ack
                a = re.search('^ack([0-9]+)', message)
                ack_dict.update({int(a.group(1)): 1})
                continue

            # EMAIL (-)
            # is email command
            elif re.search('^-.*', message):
                searchstring = '^' + CONFIG['ham']['callsign'] + '.*'
                # only I can do email
                if re.search(searchstring, fromcall):
                    # digits only, first one is number of emails to resend
                    r = re.search('^-([0-9])[0-9]*$', message)
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
                            if content == 'mapme':
                                content = (
                                    "Click for my location: http://aprs.fi/{}".
                                    format(CONFIG['ham']['callsign']))
                            too_soon = 0
                            now = time.time()
                            # see if we sent this msg number recently
                            if ack in email_sent_dict:
                                timedelta = now - email_sent_dict[ack]
                                if (timedelta < 300):  # five minutes
                                    too_soon = 1
                            if not too_soon or ack == 0:
                                send_result = send_email(to_addr, content)
                                if send_result != 0:
                                    send_message(fromcall, "-" + to_addr + " failed")
                                else:
                                    # send_message(fromcall, "-" + to_addr + " sent")
                                    if len(email_sent_dict) > 98:  # clear email sent dictionary if somehow goes over 100
                                        LOG.debug("DEBUG: email_sent_dict is big (" + str(len(email_sent_dict)) + ") clearing out.")
                                        email_sent_dict.clear()
                                    email_sent_dict[ack] = now
                            else:
                                LOG.info("Email for message number " + ack + " recently sent, not sending again.")
                    else:
                        send_message(fromcall, "Bad email address")

            # TIME (t)
            elif re.search('^[tT]', message):
                stm = time.localtime()
                h = stm.tm_hour
                m = stm.tm_min
                cur_time = fuzzy(h, m, 1)
                reply = cur_time + " (" + str(h) + ":" + str(m).rjust(2, '0') + "PDT)" + " (" + message.rstrip() + ")"
                thread = threading.Thread(target=send_message,
                                          name="send_message",
                                          args=(fromcall, reply))
                thread.start()

            # FORTUNE (f)
            elif re.search('^[fF]', message):
                process = subprocess.Popen(['/usr/games/fortune', '-s', '-n 60'], stdout=subprocess.PIPE)
                reply = process.communicate()[0]
                send_message(fromcall, reply.rstrip())

            # PING (p)
            elif re.search('^[pP]', message):
                stm = time.localtime()
                h = stm.tm_hour
                m = stm.tm_min
                s = stm.tm_sec
                reply = "Pong! " + str(h).zfill(2) + ":" + str(m).zfill(2) + ":" + str(s).zfill(2)
                send_message(fromcall, reply.rstrip())

            # LOCATION (l)  "8 Miles E Auburn CA 1771' 38.91547,-120.99500 0.1h ago"
            elif re.search('^[lL]', message):
                # get last location of a callsign, get descriptive name from weather service
                try:
                    a = re.search(r"'^.*\s+(.*)", message)   # optional second argument is a callsign to search
                    if a is not None:
                        searchcall = a.group(1)
                        searchcall = searchcall.upper()
                    else:
                        searchcall = fromcall            # if no second argument, search for calling station
                    url = "http://api.aprs.fi/api/get?name=" + searchcall + "&what=loc&apikey=104070.f9lE8qg34L8MZF&format=json"
                    response = urllib.urlopen(url)
                    aprs_data = json.loads(response.read())
                    lat = aprs_data['entries'][0]['lat']
                    lon = aprs_data['entries'][0]['lng']
                    try:  # altitude not always provided
                        alt = aprs_data['entries'][0]['altitude']
                    except Exception:
                        alt = 0
                    altfeet = int(alt * 3.28084)
                    aprs_lasttime_seconds = aprs_data['entries'][0]['lasttime']
                    aprs_lasttime_seconds = aprs_lasttime_seconds.encode('ascii', errors='ignore')  # unicode to ascii
                    delta_seconds = time.time() - int(aprs_lasttime_seconds)
                    delta_hours = delta_seconds / 60 / 60
                    url2 = "https://forecast.weather.gov/MapClick.php?lat=" + str(lat) + "&lon=" + str(lon) + "&FcstType=json"
                    response2 = urllib.urlopen(url2)
                    wx_data = json.loads(response2.read())
                    reply = searchcall + ": " + wx_data['location']['areaDescription'] + " " + str(altfeet) + "' " + str(lat) + "," + str(lon) + " " + str("%.1f" % round(delta_hours, 1)) + "h ago"
                    reply = reply.encode('ascii', errors='ignore')  # unicode to ascii
                    send_message(fromcall, reply.rstrip())
                except Exception:
                    reply = "Unable to find station " + searchcall + ".  Sending beacons?"
                    send_message(fromcall, reply.rstrip())

            # WEATHER (w)  "42F(68F/48F) Haze. Tonight, Haze then Chance Rain."
            elif re.search('^[wW]', message):
                # get my last location from aprsis then get weather from
                # weather service
                try:
                    url = ("http://api.aprs.fi/api/get?"
                           "&what=loc&apikey=104070.f9lE8qg34L8MZF&format=json"
                           "&name=%s" % fromcall)
                    response = urllib.urlopen(url)
                    aprs_data = json.loads(response.read())
                    lat = aprs_data['entries'][0]['lat']
                    lon = aprs_data['entries'][0]['lng']
                    url2 = ("https://forecast.weather.gov/MapClick.php?lat=%s"
                            "&lon=%s&FcstType=json" % (lat, lon))
                    response2 = urllib.urlopen(url2)
                    wx_data = json.loads(response2.read())
                    reply = "%sF(%sF/%sF) %s. %s, %s." % (
                        wx_data['currentobservation']['Temp'],
                        wx_data['data']['temperature'][0],
                        wx_data['data']['temperature'][1],
                        wx_data['data']['weather'][0],
                        wx_data['time']['startPeriodName'][1],
                        wx_data['data']['weather'][1])

                    # unicode to ascii
                    reply = reply.encode('ascii', errors='ignore')
                    send_message(fromcall, reply.rstrip())
                except Exception:
                    reply = "Unable to find you (send beacon?)"
                    send_message(fromcall, reply)

            # USAGE
            else:
                reply = "usage: time, fortune, loc, weath"
                send_message(fromcall, reply)

            # let any threads do their thing, then ack
            time.sleep(1)
            # send an ack last
            send_ack(fromcall, ack)

        except Exception as e:
            LOG.error("Error in mainline loop:")
            LOG.error("%s" % str(e))
            if (str(e) == "timed out" or str(e) == "Temporary failure in name resolution" or str(e) == "Network is unreachable"):
                LOG.error("Attempting to reconnect.")
                sock.shutdown(0)
                sock.close()
                setup_connection()
                sock.send("user %s pass %s vers https://github.com/craigerl/aprsd 2.00\n" % (user, password))
                continue
            # LOG.error("Exiting.")
            # os._exit(1)
            time.sleep(5)
            continue   # don't know what failed, so wait and then continue main loop again

    # end while True
    # tn.close()
    sock.shutdown(0)
    sock.close()

    exit()


if __name__ == "__main__":
    main(args)
