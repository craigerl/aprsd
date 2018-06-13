#!/usr/bin/python -u
#
# Listen on amateur radio aprs-is network for messages and respond to them.
# You must have an amateur radio callsign to use this software.  Put  your
# callsign in the "USER" variable and update your aprs-is password in "PASS".
# You must also have an imap email account available for polling.
#
# There are additional parameters in the code (sorry), so be sure to set your
# email server, and associated logins, passwords.  search for "yourmaildomain", 
# "password".  Search for "shortcuts" to setup email aliases as well.
# 
#
#
# APRS messages:
#   t(ime)                 = respond with the current time          
#   f(ortune)              = respond with a short fortune
#   -email_addr email text = send an email
#   -2                     = display the last 2 emails received
#   anything else          = respond with usage
#
# Meanwhile this code will monitor an imap mailbox and forward email
# to your BASECALLSIGN.
#
# (C)2018 Craig Lamparter
# License GPLv2
#

from fuzzyclock import fuzzy
import sys
import os
import telnetlib
import time
import re
from random import randint
import smtplib
from email.mime.text import MIMEText
import subprocess
import datetime
import calendar
from imapclient import IMAPClient, SEEN 
import email
import threading
import signal


# edit to taste, be advised there are additional parameters in the code for now

HOST = "noam.aprs2.net"     # north america tier2 servers round robin
USER = "KM6XXX-9"           # callsign of this aprs client with SSID
PASS = "22222"              # google how to generate this
BASECALLSIGN = "KM6XXX"     # callsign of radio in the field to which we send email




def signal_handler(signal, frame):
   print("Ctrl+C, exiting.")
   #sys.exit(0)  # thread ignores this
   os._exit(0)
signal.signal(signal.SIGINT, signal_handler)

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

  shortcuts = {"jl" : "jlname@email.com",  "cl" : "clname@email.com"  }
  shortcuts_inverted = dict([[v,k] for k,v in shortcuts.items()]) # swap key/value 
  
  server = IMAPClient('mail.yourmaildomain.org', use_uid=True)
  server.login('KM6XXX@yourmaildomain.org', 'password')
  select_info = server.select_folder('INBOX')

  messages = server.search(['SINCE', today])
  #print("%d messages received today" % len(messages))

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
     reply = "No new msg"
     send_message(fromcall, reply)

  server.logout()
### end resend_email()

def check_email_thread():

#  print "Email thread disabled."
#  return

  threading.Timer(55, check_email_thread).start()     # how do we skip first run?

  shortcuts = {"jl" : "jlname@email.com",  "cl" : "clname@email.com"  }
  shortcuts_inverted = dict([[v,k] for k,v in shortcuts.items()]) # swap key/value 
  
  date = datetime.datetime.now()
  month = date.strftime("%B")[:3]       # Nov, Mar, Apr
  day   = date.day
  year  = date.year
  today = str(day) + "-"  + month + "-" + str(year)
  
  server = IMAPClient('mail.yourmaildomain.org', use_uid=True)
  server.login('KM6XXX@yourmaildomain.org', 'password')
  select_info = server.select_folder('INBOX')
  
  messages = server.search(['SINCE', today])
  #print("%d messages received today" % len(messages))

  for msgid, data in server.fetch(messages, ['ENVELOPE']).items():
      envelope = data[b'ENVELOPE']
      #print('ID:%d  "%s" (%s)'  % (msgid, envelope.subject.decode(), envelope.date   ))
      f = re.search('([[A-a][0-9]_-]+@[[A-a][0-9]_-\.]+)', str(envelope.from_[0]) )
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
         send_message(BASECALLSIGN, reply)                                #radio
         server.add_flags(msgid, ['APRS'])                                 #flag message as sent via aprs
         server.remove_flags(msgid, [SEEN])                                #unset seen flag, will stay bold in email client

  server.logout()
### end check_email()

def send_ack(tocall, ack):
  tocall = tocall.ljust(9) # pad to nine chars
  line = USER + ">APRS::" + tocall + ":ack" + str(ack) + "\n"
  print "Sending ack __________________"
  print "Raw         : " + line,
  print "To          : " + tocall
  print "Ack number  : " + str(ack)
  tn.write(line)
### end send_ack()

def send_message(tocall, message):
  messagecounter = randint(10,99)
  tocall = tocall.ljust(9) # pad to nine chars
  message = message[:67]   # yaesu max length allowed, plus 3 for msg number {00 ?
  line = USER + ">APRS::" + tocall + ":" + message + "{" + str(messagecounter) + "\n"
  print "Sending message_______________"
  print "Raw         : " + line,
  print "To          : " + tocall
  print "Message     : " + message
  tn.write(line)    # resends within 8 minutes are tossed
### end send_message()

def process_message(line):
  f = re.search('^(.*)>', line)
  fromcall = f.group(1)
  searchstring = '::' + USER + '[ ]*:(.*)'    # verify this, callsign is padded out with spaces to colon
  m = re.search(searchstring, line)
  fullmessage = m.group(1)

  ack_attached = re.search('(.*){([0-9]+)', fullmessage)
  if ack_attached:                       # "{##" suffix means radio wants an ack back
     message = ack_attached.group(1)     # message content
     ack_num = ack_attached.group(2)     # suffix number to use in ack
  else:
     message = fullmessage
     ack_num = 0                         # ack not requested, but lets send one as 0
  
  print "Received message______________"
  print "Raw         : " + line
  print "From        : " + fromcall
  print "Message     : " + message
  print "Msg number  : " + str(ack_num)

  return (fromcall, message, ack_num)

### end process_message()

def send_email(to_addr, content):
  print "Sending Email_________________"
  shortcuts = {"jl" : "jlname@email.com",  "cl" : "clname@email.com"  }
  if to_addr in shortcuts:
     print "To          : " + to_addr , 
     to_addr = shortcuts[to_addr]
     print " (" + to_addr + ")"
  subject = BASECALLSIGN
  #content = content + "\n\n(NOTE: reply with one line)"
  print "Subject     : " + subject
  print "Body        : " + content 

  msg = MIMEText(content)
  msg['Subject'] = subject 
  msg['From'] = "KM6XXX@yourmaildomain.org"
  msg['To'] = to_addr
  s = smtplib.SMTP_SSL('mail.yourmaildomain.org', 465)
  s.login("KM6XXX@yourmaildomain.org", "password")
  try: 
     s.sendmail("KM6XXX@yourmaildomain.org", [to_addr], msg.as_string())
  except Exception, e:
     print "Sendmail Error!!!!!!!!!" 
     s.quit()
     return(-1)
  s.quit()
  return(0)

### main()  
try:
  tn = telnetlib.Telnet(HOST, 14580)
except Exception, e:
  print "Telnet session failed.\n"
  sys.exit(-1)

time.sleep(2)

tn.write("user " + USER + " pass " +  PASS + " vers aprsd 0.99\n" )

time.sleep(2)

check_email_thread()  # start email reader thread

while True:
  line = ""
  try: 
     for char in tn.read_until("\n",100):
       line = line + char 
     line = line.replace('\n', '')
     print line
     searchstring = '::' + USER  
     if re.search(searchstring, line):      # is aprs message to us, not beacon, status, etc
        (fromcall, message, ack) = process_message(line)
     else: 
        message = "noise"
        continue
    
     # ACK (ack##)                                                     # ignore incoming acks
     if re.search('^ack[0-9]+', message):                            
         is_ack = True                               
         continue
   
     # EMAIL (-)
     elif re.search('^-.*', message):                                 # is email command
         searchstring = '^' + BASECALLSIGN + '.*'
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
                      content = "Click for my location: http://aprs.fi/" + BASECALLSIGN 
                  send_result = send_email(to_addr, content)  
                  if send_result != 0:
                      send_message(fromcall, "-" + to_addr + " failed")
                  else:
                      send_message(fromcall, "-" + to_addr + " sent")
            else:
               send_message(fromcall, "Bad email address")

     # TIME (t) 
     elif re.search('^t', message):  
        stm = time.localtime()
        h = stm.tm_hour
        m = stm.tm_min
        cur_time = fuzzy(h, m, 1)
        reply = cur_time + " (" + str(h) + ":" + str(m).rjust(2, '0') + "PDT)" + " (" + message.rstrip() + ")"
        send_message(fromcall, reply)

     # FORTUNE (f)
     elif re.search('^f', message):  
        process = subprocess.Popen(['/usr/games/fortune', '-s', '-n 60'], stdout=subprocess.PIPE)
        reply = process.communicate()[0]
        send_message(fromcall, reply.rstrip())

     # USAGE
     else:
        reply = "APRSd v0.99.  Commands: t(ime), f(ortune), -(emailaddr emailbody)"
        send_message(fromcall, reply)

     send_ack(fromcall, ack)           # send an ack last

  except Exception, e:
     print "Error in mainline loop:"
     print "%s" % str(e)
     print "Exiting."
     #sys.exit(1)  # merely a suggestion
     os._exit(1)
  
# end while True

tn.close()

exit()
