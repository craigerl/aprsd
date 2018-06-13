# aprsd

Listen on amateur radio aprs-is network for messages and respond to them.
You must have an amateur radio callsign to use this software.  Put  your
callsign in the "USER" variable and update your aprs-is password in "PASS".
You must also have an imap email account available for polling.

Current messages this will respond to:
'''
APRS messages:
   t(ime)                 = respond with the current time
   f(ortune)              = respond with a short fortune (requires fuzzyclock python module)
   -email_addr email text = send an email
   -2                     = display the last 2 emails received
   anything else          = respond with usage
'''
 Meanwhile this code will monitor an imap mailbox and forward email
 to your BASECALLSIGN over the air.


There are additional parameters in the code (sorry), so be sure to set your
email server, and associated logins, passwords.  search for "yourmaildomain",
"password".  Search for "shortcuts" to setup email aliases as well.


Example usage:

```
craiger@pc:~/ham/aprsd$ ./aprsd.py
# aprsc 2.1.4-g408ed49
# logresp KM6LYW-9 verified, server T2TEXAS
# aprsc 2.1.4-g408ed49 31 Oct 2017 17:42:54 GMT T2TEXAS 205.209.228.93:14580
Received message______________
Raw        : KM6LYW>APY01D,ALDER*,WIDE2-1,qAR,N6VUD-15::KM6LYW-9 :Test31{53
From       : KM6LYW
Message    : Test31
Ack number : 53
Sending ack __________________
Raw        : KM6LYW-9>APRS,TCPIP*::KM6LYW   :ack53
To         : KM6LYW   
Ack number : 53
Sending reply_________________
Raw        : KM6LYW-9>APRS,TCPIP*::KM6LYW   :Current time: 14:57:06 10/31/2017 PDT  (Test31){964
To         : KM6LYW   
Message    : Current time: 14:57:06 10/31/2017 PDT  (Test31)
# aprsc 2.1.4-g408ed49 31 Oct 2017 21:57:54 GMT T2TEXAS 205.209.228.93:14580
Received message______________
Raw        : KM6LYW>APY01D,ALDER*,WIDE2-1,qAR,W6SRR-3::KM6LYW-9 :ack964
From       : KM6LYW
Message    : ack964
Ack number : none
Reply?     : No, we do not reply to ack.
# aprsc 2.1.4-g408ed49 31 Oct 2017 17:43:14 GMT T2TEXAS 205.209.228.93:14580
# aprsc 2.1.4-g408ed49 31 Oct 2017 17:43:34 GMT T2TEXAS 205.209.228.93:14580

```
