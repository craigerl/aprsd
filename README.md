# aprsd

Listen on amateur radio aprs-is network for messages and respond to them.
You must have an amateur radio callsign to use this software.  Put  your
callsign in the "USER" variable and update your aprs-is password in "PASS".
You must also have an imap email account available for polling.

Current messages this will respond to:
```
APRS messages:
   l(ocation)             = descriptive location of calling station
                            8 Miles E Auburn CA 1673' 38.91150,-120.93450 0.1h ago
   w(eather)              = temp, (hi/low) forecast, later forecast
                            58F(58F/46F) Heavy Rain. Tonight, Heavy Rain.
   t(ime)                 = respond with the current time
   f(ortune)              = respond with a short fortune
   -email_addr email text = send an email
   -2                     = display the last 2 emails received
   p(ing)                 = respond with Pong!/time
   anything else          = respond with usage

```
 Meanwhile this code will monitor an imap mailbox and forward email
 to your BASECALLSIGN over the air.

There are additional parameters in the code (sorry), so be sure to set your
email server, and associated logins, passwords.  search for "yourdomain",
"password".  Search for "shortcuts" to setup email aliases as well.


Example usage:
```
./aprsd.py
```

Example output:

SEND EMAIL

```
Received message______________
Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :-user@host.com test new shortcuts global, radio to pc{29
From        : KM6XXX
Message     : -user@host.com test new shortcuts global, radio to pc
Msg number  : 29

Sending Email_________________
To          : cl  (craig@craiger.org)
Subject     : KM6XXX
Body        : test new shortcuts global, radio to pc

Sending ack __________________ Tx(3)
Raw         : KM6XXX-9>APRS::KM6XXX   :ack29
To          : KM6XXX   
Ack number  : 29

```

WEATHER

```
Received message______________                                                                                                                    
Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :weather{27                                                                                 
From        : KM6XXX                                                                                                                                   
Message     : weather                                                                                                                                  
Msg number  : 27                                                                                                                                       

Sending message_______________ 6(Tx3)                                                                                                                     
Raw         : KM6XXX-9>APRS::KM6XXX   :58F(58F/46F) Heavy Rain. Tonight, Heavy Rain.{6                                                                    
To          : KM6XXX                                                                                                                                          
Message     : 58F(58F/46F) Heavy Rain. Tonight, Heavy Rain.                                                                                                   

Sending ack __________________ Tx(3)                                                                                                                          
Raw         : KM6XXX-9>APRS::KM6XXX   :ack27                                                                                                                  
To          : KM6XXX                                                                                                                                             
Ack number  : 27   

Received message______________
Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :ack6
From        : KM6XXX
Message     : ack6
Msg number  : 0
``` 


LOCATION

```
Received message______________
Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :location{28
From        : KM6XXX
Message     : location
Msg number  : 28

Sending message_______________ 7(Tx3)
Raw         : KM6XXX-9>APRS::KM6XXX   :8 Miles E Auburn CA 1673' 38.91150,-120.93450 0.1h ago{7
To          : KM6XXX   
Message     : 8 Miles E Auburn CA 1673' 38.91150,-120.93450 0.1h ago

Sending ack __________________ Tx(3)
Raw         : KM6XXX-9>APRS::KM6XXX   :ack28
To          : KM6XXX   
Ack number  : 28

Received message______________
Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :ack7
From        : KM6XXX
Message     : ack7
Msg number  : 0

```


AND... ping, fortune, time.....
