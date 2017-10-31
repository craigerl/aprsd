# aprsd
Amateur radio APRS client which listens for APRS messages and replies.  This is essentially a way for you to send commands to your PC from your Amateur radio and have it respond with something interesting.  Perhaps you could make a bot?  Like WXBOT?  It currently just "echoes" what it receives.

Please change callsign and aprs password throughout code (not just at top).

Example usage:

```
craiger@pc:~/ham/aprsd$ ./aprsd.py
# aprsc 2.1.4-g408ed49
# logresp KM6LYW-9 verified, server T2TEXAS
# aprsc 2.1.4-g408ed49 31 Oct 2017 17:42:54 GMT T2TEXAS 205.209.228.93:14580
Received message______________
Raw        : KM6LYW>APY01D,ALDER*,WIDE2-1,qAR,W6SRR-3::KM6LYW-9 :Test4 - please reply{22
From       : KM6LYW
Message    : Test4 - please reply
Ack number : 22
Sending ack __________________
Raw        : KM6LYW-9>APRS,TCPIP*::KM6LYW   :ack22
To         : KM6LYW   
Ack number : 22
Sending message_______________
Raw        : KM6LYW-9>APRS,TCPIP*::KM6LYW   :Echo: Test4 - please reply
To         : KM6LYW   
Message    : Echo: Test4 - please reply
# aprsc 2.1.4-g408ed49 31 Oct 2017 17:43:14 GMT T2TEXAS 205.209.228.93:14580
# aprsc 2.1.4-g408ed49 31 Oct 2017 17:43:34 GMT T2TEXAS 205.209.228.93:14580

```
