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
import pprint
import re
import signal
import smtplib
import subprocess
import sys
import telnetlib
import threading
import time
import urllib

from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler

# external lib imports
from imapclient import IMAPClient, SEEN

# local imports here
from aprsd.fuzzyclock import fuzzy
import utils

# setup the global logger
LOG = logging.getLogger('APRSD')

# global for the config yaml
CONFIG = None

# localization, please edit:
# HOST = "noam.aprs2.net"     # north america tier2 servers round robin
# USER = "KM6XXX-9"           # callsign of this aprs client with SSID
# PASS = "99999"              # google how to generate this
# BASECALLSIGN = "KM6XXX"     # callsign of radio in the field to which we send email
# shortcuts = {
#   "aa" : "5551239999@vtext.com",
#   "cl" : "craiglamparter@somedomain.org",
#   "wb" : "5553909472@vtext.com"
# }

# globals - tell me a better way to update data being used by threads
email_sent_dict = {}  # message_number:time combos so we don't resend the same email in five mins {int:int}
ack_dict = {}         # message_nubmer:ack  combos so we stop sending a message after an ack from radio {int:int}
message_number = 0    # current aprs radio message number, increments for each message we send over rf {int}

# global telnet connection object
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


def setup_connection():
    global tn
    host = CONFIG['aprs']['host']
    port = CONFIG['aprs']['port']
    LOG.debug("Setting up telnet connection to '%s:%s'" % (host, port))
    try:
        tn = telnetlib.Telnet(host, port)
    except Exception, e:
        LOG.exception("Telnet session failed.")
        sys.exit(-1)


def signal_handler(signal, frame):
    LOG.info("Ctrl+C, exiting.")
    #sys.exit(0)  # thread ignores this
    os._exit(0)

### end signal_handler

def parse_email(msgid, data, server):
  envelope = data[b'ENVELOPE']
  #print('ID:%d  "%s" (%s)'  % (msgid, envelope.subject.decode(), envelope.date   ))
  f = re.search('([\.\w_-]+@[\.\w_-]+)', str(envelope.from_[0]) )  # email address match
  if f is not None:
     from_addr = f.group(1)
  else:
     from_addr = "noaddr"
  m = server.fetch([msgid], ['RFC822'])
  msg = email.message_from_string(m[msgid]['RFC822'])
  if msg.is_multipart():
    text = ""
    html = None
    body = "* unreadable msg received" # default in case body somehow isn't set below - happened once
    for part in msg.get_payload():
       if part.get_content_charset() is None:
           # We cannot know the character set, so return decoded "something"
           text = part.get_payload(decode=True)
           continue

       charset = part.get_content_charset()

       if part.get_content_type() == 'text/plain':
           text = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')

       if part.get_content_type() == 'text/html':
           html = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')

       if text is not None:
          body = text.strip()  # strip removes white space fore and aft of string
       else:
          body = html.strip()
  else:
     text = unicode(msg.get_payload(decode=True), msg.get_content_charset(), 'ignore').encode('utf8', 'replace')
     body = text.strip()

  body = re.sub('<[^<]+?>', '', body)                  # strip all html tags
  body = body.replace("\n", " ").replace("\r", " ")    # strip CR/LF, make it one line, .rstrip fails at this
  return(body, from_addr)
## end parse_email


def resend_email(count):
    date  = datetime.datetime.now()
    month = date.strftime("%B")[:3]       # Nov, Mar, Apr
    day   = date.day
    year  = date.year
    today = str(day) + "-"  + month + "-" + str(year)

    shortcuts = CONFIG['shortcuts']
    shortcuts_inverted = dict([[v,k] for k,v in shortcuts.items()]) # swap key/value

    LOG.debug("resend_email: Connect to IMAP host '%s' with user '%s'" %
              (CONFIG['imap']['host'],
               CONFIG['imap']['login']))
    server = IMAPClient(CONFIG['imap']['host'], use_uid=True)
    server.login(CONFIG['imap']['login'], CONFIG['imap']['password'])
    # select_info = server.select_folder('INBOX')

    messages = server.search(['SINCE', today])
    LOG.debug("%d messages received today" % len(messages))

    msgexists = False

    messages.sort(reverse=True)
    del messages[int(count):]          # only the latest "count" messages
    for message in messages:
        for msgid, data in list(server.fetch(message, ['ENVELOPE']).items()):   # one at a time, otherwise order is random
            (body, from_addr) = parse_email(msgid, data, server)
            server.remove_flags(msgid, [SEEN])                                  # unset seen flag, will stay bold in email client
            if from_addr in shortcuts_inverted:                                 # reverse lookup of a shortcut
                from_addr = shortcuts_inverted[from_addr]
            reply = "-" + from_addr + " * " + body                              # asterisk indicates a resend
            send_message(fromcall, reply)
            msgexists = True

    if msgexists is not True:
        stm = time.localtime()
        h = stm.tm_hour
        m = stm.tm_min
        s = stm.tm_sec
        # append time as a kind of serial number to prevent FT1XDR from thinking this is a duplicate message.
        # The FT1XDR pretty much ignores the aprs message number in this regard.  The FTM400 gets it right.
        reply = "No new msg " + str(h).zfill(2) + ":" + str(m).zfill(2) + ":" + str(s).zfill(2)
        send_message(fromcall, reply)

    server.logout()
### end resend_email()

def check_email_thread():
    #  print "Email thread disabled."
    #  return

    LOG.debug("Starting Email thread")
    threading.Timer(55, check_email_thread).start()     # how do we skip first run?

    shortcuts = CONFIG['shortcuts']
    shortcuts_inverted = dict([[v,k] for k,v in shortcuts.items()]) # swap key/value

    date = datetime.datetime.now()
    month = date.strftime("%B")[:3]       # Nov, Mar, Apr
    day   = date.day
    year  = date.year
    today = str(day) + "-"  + month + "-" + str(year)

    LOG.debug("Connect to IMAP host '%s' with user '%s'" %
              (CONFIG['imap']['host'],
               CONFIG['imap']['login']))

    try:
        server = IMAPClient(CONFIG['imap']['host'], use_uid=True, timeout=5)
        server.login(CONFIG['imap']['login'], CONFIG['imap']['password'])
    except Exception:
        LOG.exception("Failed to login with IMAP server")
        return

    if 'gmail' in CONFIG['imap']['host'].lower():
        server.select_folder('INBOX')

    messages = server.search(['SINCE', today])
    LOG.debug("%d messages received today" % len(messages))

    for msgid, data in server.fetch(messages, ['ENVELOPE']).items():
        envelope = data[b'ENVELOPE']
        LOG.debug('ID:%d  "%s" (%s)' %
                  (msgid, envelope.subject.decode(), envelope.date))
        f = re.search('([[A-a][0-9]_-]+@[[A-a][0-9]_-\.]+)',
                      str(envelope.from_[0]) )
        if f is not None:
            from_addr = f.group(1)
        else:
            from_addr = "noaddr"

        if "APRS" not in server.get_flags(msgid)[msgid]:                     #if msg not flagged as sent via aprs
            m = server.fetch([msgid], ['RFC822'])
            (body, from_addr) = parse_email(msgid, data, server)
            server.remove_flags(msgid, [SEEN])                                # unset seen flag, will stay bold in email client

            if from_addr in shortcuts_inverted:                               # reverse lookup of a shortcut
                from_addr = shortcuts_inverted[from_addr]

            reply = "-" + from_addr + " " + body
            #print "Sending message via aprs: " + reply
            send_message(CONFIG['ham']['callsign'], reply)                                #radio
            server.add_flags(msgid, ['APRS'])                                 #flag message as sent via aprs
            server.remove_flags(msgid, [SEEN])                                #unset seen flag, will stay bold in email client

    server.logout()
### end check_email()


def send_ack_thread(tocall, ack, retry_count):
  tocall = tocall.ljust(9) # pad to nine chars
  line = CONFIG['aprs']['login'] + ">APRS::" + tocall + ":ack" + str(ack) + "\n"
  for i in range(retry_count, 0, -1):
     LOG.info("Sending ack __________________ Tx(" + str(i) + ")")
     LOG.info("Raw         : " + line)
     LOG.info("To          : " + tocall)
     LOG.info("Ack number  : " + str(ack))
     tn.write(line)
     time.sleep(31)  # aprs duplicate detection is 30 secs?  (21 only sends first, 28 skips middle)
  return()
### end_send_ack_thread


def send_ack(tocall, ack):
  retry_count = 3
  thread = threading.Thread(target = send_ack_thread, args = (tocall, ack, retry_count))
  thread.start()
  return()
### end send_ack()


def send_message_thread(tocall, message, this_message_number, retry_count):
  global ack_dict
  line = (CONFIG['aprs']['login'] + ">APRS::" + tocall + ":" + message +
          "{" + str(this_message_number) + "\n")
  for i in range(retry_count, 0, -1):
      LOG.debug("DEBUG: send_message_thread msg:ack combos are: ")
      LOG.debug(pprint.pformat(ack_dict))
      if ack_dict[this_message_number] != 1:
         LOG.info("Sending message_______________ " +
                  str(this_message_number) + "(Tx" + str(i) + ")")
         LOG.info("Raw         : " + line)
         LOG.info("To          : " + tocall)
         LOG.info("Message     : " + message)
         tn.write(line)
         sleeptime = (retry_count - i + 1) * 31  # decaying repeats, 31 to 93 second intervals
         time.sleep(sleeptime)
      else:
         break
  return
### end send_message_thread


def send_message(tocall, message):
    global message_number
    global ack_dict
    retry_count = 3
    if message_number > 98:        # global
        message_number = 0
    message_number += 1
    if len(ack_dict) > 90:          # empty ack dict if it's really big, could result in key error later
        LOG.debug("DEBUG: Length of ack dictionary is big at " + str(len(ack_dict)) + " clearing.")
        ack_dict.clear()
        LOG.debug(pprint.pformat(ack_dict))
        LOG.debug("DEBUG: Cleared ack dictionary, ack_dict length is now " + str(len(ack_dict)) + ".")
    ack_dict[message_number] = 0   # clear ack for this message number
    tocall = tocall.ljust(9)       # pad to nine chars
    message = message[:67]         # max?  ftm400 displays 64, raw msg shows 74
                                    # and ftm400-send is max 64.  setting this to
                                    # 67 displays 64 on the ftm400. (+3 {01 suffix)
                                    # feature req: break long ones into two msgs
    thread = threading.Thread(
        target = send_message_thread,
        args = (tocall, message, message_number, retry_count))
    thread.start()
    return()
### end send_message()


def process_message(line):
    f = re.search('^(.*)>', line)
    fromcall = f.group(1)
    searchstring = '::' + CONFIG['aprs']['login'] + '[ ]*:(.*)'    # verify this, callsign is padded out with spaces to colon
    m = re.search(searchstring, line)
    fullmessage = m.group(1)

    ack_attached = re.search('(.*){([0-9A-Z]+)', fullmessage)    # ack formats include: {1, {AB}, {12
    if ack_attached:                       # "{##" suffix means radio wants an ack back
        message = ack_attached.group(1)     # message content
        ack_num = ack_attached.group(2)     # suffix number to use in ack
    else:
        message = fullmessage
        ack_num = "0"                        # ack not requested, but lets send one as 0

    LOG.info("Received message______________")
    LOG.info("Raw         : " + line)
    LOG.info("From        : " + fromcall)
    LOG.info("Message     : " + message)
    LOG.info("Msg number  : " + str(ack_num))

    return (fromcall, message, ack_num)
### end process_message()


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
    s = smtplib.SMTP_SSL(CONFIG['smtp']['host'],
                         CONFIG['smtp']['port'])
    s.login(CONFIG['smtp']['login'],
            CONFIG['smtp']['password'])
    try:
        s.sendmail(CONFIG['smtp']['login'], [to_addr], msg.as_string())
    except Exception:
        LOG.exception("Sendmail Error!!!!!!!!!")
        s.quit()
        return(-1)
    s.quit()
    return(0)
### end send_email


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
    log_format = ("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]"
                  " %(message)s")
    date_format = '%m/%d/%Y %I:%M:%S %p'
    log_formatter = logging.Formatter(fmt=log_format,
                                      datefmt=date_format)
    fh = RotatingFileHandler(CONFIG['aprs']['logfile'],
                             maxBytes=(10248576*5),
                             backupCount=4)
    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    if not args.quiet:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        LOG.addHandler(sh)


### main() ###
def main(args=args):
    global CONFIG

    CONFIG = utils.parse_config(args)
    signal.signal(signal.SIGINT, signal_handler)
    LOG.info("APRSD Started")
    LOG.debug(CONFIG)
    setup_logging(args)

    time.sleep(2)
    setup_connection()

    user = CONFIG['aprs']['login']
    password = CONFIG['aprs']['password']
    LOG.info("LOGIN to APRSD with user '%s'" % user)
    tn.write("user %s pass %s vers aprsd 0.99\n" % (user, password) )
    time.sleep(2)

    check_email_thread()  # start email reader thread

    LOG.info("Start main loop")
    while True:
        line = ""
        try:
            for char in tn.read_until("\n",100):
                line = line + char
            line = line.replace('\n', '')
            LOG.info(line)
            searchstring = '::' + user
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
                ack_dict.update({int(a.group(1)):1})
                continue

            # EMAIL (-)
            elif re.search('^-.*', message):                                 # is email command
                searchstring = '^' + CONFIG['ham']['callsign'] + '.*'
                if re.search(searchstring, fromcall):                        # only I can do email
                    r = re.search('^-([0-9])[0-9]*$', message)                # digits only, first one is number of emails to resend
                    if r is not None:
                        resend_email(r.group(1))
                    elif re.search('^-([A-Za-z0-9_\-\.@]+) (.*)', message):   # -user@address.com body of email
                        a = re.search('^-([A-Za-z0-9_\-\.@]+) (.*)', message)  # (same search again)
                        if a is not None:
                            to_addr = a.group(1)
                            content = a.group(2)
                            if content == 'mapme':                               # send recipient link to aprs.fi map
                                content = "Click for my location: http://aprs.fi/" + CONFIG['ham']['callsign']
                            too_soon = 0
                            now = time.time()
                            if ack in email_sent_dict:   # see if we sent this msg number recently
                                timedelta = now - email_sent_dict[ack]
                                if ( timedelta < 300 ):  # five minutes
                                    too_soon = 1
                            if not too_soon or ack == 0:
                                send_result = send_email(to_addr, content)
                                if send_result != 0:
                                    send_message(fromcall, "-" + to_addr + " failed")
                                else:
                                    #send_message(fromcall, "-" + to_addr + " sent")
                                    if len(email_sent_dict) > 98:  # clear email sent dictionary if somehow goes over 100
                                        LOG.debug("DEBUG: email_sent_dict is big (" + str(len(email_sent_dict)) + ") clearing out.")
                                        email_sent_dict.clear()
                                    email_sent_dict[ack] = now
                            else:
                                LOG.info("Email for message number " + ack + " recently sent, not sending again.")
                    else:
                        send_message(fromcall, "Bad email address")

            # TIME (t)
            elif re.search('^t', message):
                stm = time.localtime()
                h = stm.tm_hour
                m = stm.tm_min
                cur_time = fuzzy(h, m, 1)
                reply = cur_time + " (" + str(h) + ":" + str(m).rjust(2, '0') + "PDT)" + " (" + message.rstrip() + ")"
                thread = threading.Thread(target = send_message, args = (fromcall, reply))
                thread.start()

            # FORTUNE (f)
            elif re.search('^f', message):
                process = subprocess.Popen(['/usr/games/fortune', '-s', '-n 60'], stdout=subprocess.PIPE)
                reply = process.communicate()[0]
                send_message(fromcall, reply.rstrip())

            # PING (p)
            elif re.search('^p', message):
                stm = time.localtime()
                h = stm.tm_hour
                m = stm.tm_min
                s = stm.tm_sec
                reply = "Pong! " + str(h).zfill(2) + ":" + str(m).zfill(2) + ":" + str(s).zfill(2)
                send_message(fromcall, reply.rstrip())

            # LOCATION (l)  "8 Miles E Auburn CA 1771' 38.91547,-120.99500 0.1h ago"
            elif re.search('^l', message):
                # get my last location, get descriptive name from weather service
                try:
                    url = "http://api.aprs.fi/api/get?name=" + fromcall + "&what=loc&apikey=104070.f9lE8qg34L8MZF&format=json"
                    response = urllib.urlopen(url)
                    aprs_data = json.loads(response.read())
                    lat =  aprs_data['entries'][0]['lat']
                    lon =  aprs_data['entries'][0]['lng']
                    try:  # altitude not always provided
                        alt =  aprs_data['entries'][0]['altitude']
                    except:
                        alt = 0
                    altfeet = int(alt *  3.28084)
                    aprs_lasttime_seconds = aprs_data['entries'][0]['lasttime']
                    aprs_lasttime_seconds = aprs_lasttime_seconds.encode('ascii',errors='ignore')  #unicode to ascii
                    delta_seconds = time.time() - int(aprs_lasttime_seconds)
                    delta_hours = delta_seconds / 60 / 60
                    url2 = "https://forecast.weather.gov/MapClick.php?lat=" + str(lat) + "&lon=" + str(lon) + "&FcstType=json"
                    response2 = urllib.urlopen(url2)
                    wx_data = json.loads(response2.read())
                    reply = wx_data['location']['areaDescription'] + " " + str(altfeet) + "' " + str(lat) + "," + str(lon) + " " + str("%.1f" % round(delta_hours,1)) + "h ago"
                    reply = reply.encode('ascii',errors='ignore')  # unicode to ascii
                    send_message(fromcall, reply.rstrip())
                except:
                    reply = "Unable to find you (send beacon?)"
                    send_message(fromcall, reply.rstrip())

            # WEATHER (w)  "42F(68F/48F) Haze. Tonight, Haze then Chance Rain."
            elif re.search('^w', message):
                # get my last location from aprsis then get weather from weather service
                try:
                    url = "http://api.aprs.fi/api/get?name=" + fromcall + "&what=loc&apikey=104070.f9lE8qg34L8MZF&format=json"
                    response = urllib.urlopen(url)
                    aprs_data = json.loads(response.read())
                    lat =  aprs_data['entries'][0]['lat']
                    lon =  aprs_data['entries'][0]['lng']
                    url2 = "https://forecast.weather.gov/MapClick.php?lat=" + str(lat) + "&lon=" + str(lon) + "&FcstType=json"
                    response2 = urllib.urlopen(url2)
                    wx_data = json.loads(response2.read())
                    reply = wx_data['currentobservation']['Temp'] + "F(" + wx_data['data']['temperature'][0] + "F/" + wx_data['data']['temperature'][1] + "F) " + wx_data['data']['weather'][0] + ". " +  wx_data['time']['startPeriodName'][1] + ", " + wx_data['data']['weather'][1] + "."
                    reply = reply.encode('ascii',errors='ignore')  # unicode to ascii
                    send_message(fromcall, reply.rstrip())
                except:
                    reply = "Unable to find you (send beacon?)"
                    send_message(fromcall, reply)

            # USAGE
            else:
                reply = "usage: time, fortune, loc, weath, -emailaddr emailbody, -#(resend)"
                send_message(fromcall, reply)

            time.sleep(1)                     # let any threads do their thing, then ack
            send_ack(fromcall, ack)           # send an ack last

        except Exception, e:
            LOG.error("Error in mainline loop:")
            LOG.error("%s" % str(e))
            LOG.error("Exiting.")
            #sys.exit(1)  # merely a suggestion
            os._exit(1)

    # end while True
    tn.close()
    exit()


if __name__ == "__main__":
    main(args)