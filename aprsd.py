#!/usr/bin/python

# example incoming message:
# KM6LYW>APRS,TCPIP*,qAC,FOURTH::KM6LYW-4 :test message to telnet
# KM6LYW-4>APRS,TCPIP*,qAC,T2TEXAS::KM6LYW-9 :This is a test message
#
# from radio:
# KM6LYW>APY01D,PINE*,WIDE2-1,qAR,KJ6NKR-2::KM6LYW-9 :time please{15

import sys
import telnetlib
import time
import re
from random import randint

HOST = "texas.aprs2.net"
USER = "KM6LYW-9"
PASS = "11111"

def send_ack(tocall, ack):
  tocall = tocall.ljust(9) # pad to nine chars
  line = "KM6LYW-9>APRS,TCPIP*::" + tocall + ":ack" + ack + "\n"
  print "Sending ack __________________"
  print "Raw        : " + line,
  print "To         : " + tocall
  print "Ack number : " + ack
  tn.write(line)

def send_message(tocall, message):
  messagecounter = randint(100,999)
  tocall = tocall.ljust(9) # pad to nine chars
  line = "KM6LYW-9>APRS,TCPIP*::" + tocall + ":" + message + "{" + str(messagecounter) + "\n"
  print "Sending message_______________"
  print "Raw        : " + line,
  print "To         : " + tocall
  print "Message    : " + message
  tn.write(line)
### end send_ack()

def process_message(line):
  f = re.search('(.*)>', line)
  fromcall = f.group(1)
  m = re.search('::KM6LYW-9 :(.*)', line)
  fullmessage = m.group(1)
  searchresult = re.search('(.*){(.*)', fullmessage)

  if searchresult:
    message= searchresult.group(1)
    ack = searchresult.group(2)
  else:
    message = fullmessage
    ack = "none"

  print "Received message______________"
  print "Raw        : " + line
  print "From       : " + fromcall
  print "Message    : " + message
  print "Ack number : " + ack

  if not re.search('^ack[0-9]*', message):
    send_ack(fromcall, ack)
    reply = "Echo: " + message
    send_message(fromcall, reply)
  else:
  print "Reply reqd :  This is an ack, not replying."


### end process_message()
  
tn = telnetlib.Telnet(HOST, 14580)

time.sleep(2)
tn.write("user " + USER + " pass " +  PASS + " vers aprsd 0.99\n" )

while True:
  line = ""
  for char in tn.read_until("\n",100):
    line = line + char 
  line = line.replace('\n', '')
  if re.search("::KM6LYW-9 ", line):
     process_message(line)
  else:
     print line

  
# end while True

tn.close()

exit()
######################################### Notes... ##########

#for line in tn.expect(msg_regex):
#  print ("%s\n") % line 

#for line in tn.read_all():
#  print ("%s\n") % line 

tn.close()


#input = tn.read_until("::KM6LYW-4 :") 
#tn.write(user + "\n")
#if password:
#    tn.read_until("Password: ")
#    tn.write(password + "\n")
#
#tn.write("ls\n")
#tn.write("exit\n")

print tn.read_all()
