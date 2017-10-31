# aprsd
Amateur radio APRS client which listens for APRS messages and replies.  This is essentially a way for you to send commands to your PC from your Amateur radio and have it respond with something interesting.  Perhaps you could make a bot?  Like WXBOT?  It currently just replies with the current time.

Please change callsign and aprs password throughout code (not just at top).

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
