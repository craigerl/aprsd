=====
APRSD
=====

.. image:: https://github.com/craigerl/aprsd/workflows/python/badge.svg
    :target: https://github.com/craigerl/aprsd/actions

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://black.readthedocs.io/en/stable/

.. image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
    :target: https://timothycrosley.github.io/isort/

Listen on amateur radio aprs-is network for messages and respond to them.
You must have an amateur radio callsign to use this software.  Put  your
callsign in the "USER" variable and update your aprs-is password in "PASS".
You must also have an imap email account available for polling.

Current messages this will respond to:
--------------------------------------

::

  APRS messages:
   l(ocation) [callsign]  = descriptive current location of your radio
                            8 Miles E Auburn CA 1673' 39.92150,-120.93950 0.1h ago
   w(eather)              = weather forecast for your radio's current position
                            58F(58F/46F) Partly Cloudy. Tonight, Heavy Rain.
   t(ime)                 = respond with the current time
   f(ortune)              = respond with a short fortune
   -email_addr email text = send an email, say "mapme" to send a current position/map
   -2                     = resend the last 2 emails from your imap inbox to this radio
   p(ing)                 = respond with Pong!/time
   anything else          = respond with usage


Meanwhile this code will monitor a single imap mailbox and forward email
to your BASECALLSIGN over the air.  Only radios using the BASECALLSIGN are allowed
to send email, so consider this security risk before using this (or Amatuer radio in
general).  Email is single user at this time.

There are additional parameters in the code (sorry), so be sure to set your
email server, and associated logins, passwords.  search for "yourdomain",
"password".  Search for "shortcuts" to setup email aliases as well.


Installation:
-------------

  pip install aprsd

Example usage:
--------------

  aprsd -h

Example output:
---------------

SEND EMAIL (radio to smtp server)
---------------------------------

::

    Received message______________
    Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :-user@host.com test new shortcuts global, radio to pc{29
    From        : KM6XXX
    Message     : -user@host.com test new shortcuts global, radio to pc
    Msg number  : 29

    Sending Email_________________
    To          : user@host.com
    Subject     : KM6XXX
    Body        : test new shortcuts global, radio to pc

    Sending ack __________________ Tx(3)
    Raw         : KM6XXX-9>APRS::KM6XXX   :ack29
    To          : KM6XXX
    Ack number  : 29


RECEIVE EMAIL (imap server to radio)
------------------------------------

::

    Sending message_______________ 6(Tx3)
    Raw         : KM6XXX-9>APRS::KM6XXX   :-somebody@gmail.com email from internet to radio{6
    To          : KM6XXX
    Message     : -somebody@gmail.com email from internet to radio

    Received message______________
    Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :ack6
    From        : KM6XXX
    Message     : ack6
    Msg number  : 0


WEATHER
-------

::

    Received message______________
    Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :weather{27
    From        : KM6XXX
    Message     : weather
    Msg number  : 27

    Sending message_______________ 6(Tx3)
    Raw         : KM6XXX-9>APRS::KM6XXX   :58F(58F/46F) Partly cloudy. Tonight, Heavy Rain.{6
    To          : KM6XXX
    Message     : 58F(58F/46F) Party Cloudy. Tonight, Heavy Rain.

    Sending ack __________________ Tx(3)
    Raw         : KM6XXX-9>APRS::KM6XXX   :ack27
    To          : KM6XXX
    Ack number  : 27

    Received message______________
    Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :ack6
    From        : KM6XXX
    Message     : ack6
    Msg number  : 0


LOCATION
--------

::

    Received message______________
    Raw         : KM6XXX>APY400,WIDE1-1,qAO,KM6XXX-1::KM6XXX-9 :location{28
    From        : KM6XXX
    Message     : location
    Msg number  : 28

    Sending message_______________ 7(Tx3)
    Raw         : KM6XXX-9>APRS::KM6XXX   :8 Miles NE Auburn CA 1673' 39.91150,-120.93450 0.1h ago{7
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



AND... ping, fortune, time.....
