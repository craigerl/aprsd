APRSD server
============

Running the APRSD server
------------------------

Once APRSD is :doc:`installed <install>` and :doc:`configured <configure>` the server can be started by
running.

.. code-block:: shell

   aprsd server

The server will start several threads to deal handle incoming messages, outgoing
messages, checking and sending email.

.. code-block:: shell

    [MainThread  ] [INFO ] APRSD Started version: 1.5.1
    [MainThread  ] [INFO ] Checking IMAP configuration
    [MainThread  ] [INFO ] Checking SMTP configuration
    [MainThread  ] [DEBUG] Connect to SMTP host SSL smtp.gmail.com:465 with user 'test@hemna.com'
    [MainThread  ] [DEBUG] Connected to smtp host SSL smtp.gmail.com:465
    [MainThread  ] [DEBUG] Logged into SMTP server SSL smtp.gmail.com:465
    [MainThread  ] [INFO ] Validating 2 Email shortcuts. This can take up to 10 seconds per shortcut
    [MainThread  ] [ERROR] 'craiglamparter@somedomain.org' is an invalid email address. Removing shortcut
    [MainThread  ] [INFO ] Available shortcuts: {'wb': 'waboring@hemna.com'}
    [MainThread  ] [INFO ] Loading Core APRSD Command Plugins
    [MainThread  ] [INFO ] Registering Command plugin 'aprsd.plugins.email.EmailPlugin'(1.0)  '^-.*'
    [MainThread  ] [INFO ] Registering Command plugin 'aprsd.plugins.fortune.FortunePlugin'(1.0)  '^[fF]'
    [MainThread  ] [INFO ] Registering Command plugin 'aprsd.plugins.location.LocationPlugin'(1.0)  '^[lL]'
    [MainThread  ] [INFO ] Registering Command plugin 'aprsd.plugins.ping.PingPlugin'(1.0)  '^[pP]'
    [MainThread  ] [INFO ] Registering Command plugin 'aprsd.plugins.query.QueryPlugin'(1.0)  '^\?.*'
    [MainThread  ] [INFO ] Registering Command plugin 'aprsd.plugins.time.TimePlugin'(1.0)  '^[tT]'
    [MainThread  ] [INFO ] Registering Command plugin 'aprsd.plugins.weather.WeatherPlugin'(1.0)  '^[wW]'
    [MainThread  ] [INFO ] Registering Command plugin 'aprsd.plugins.version.VersionPlugin'(1.0)  '^[vV]'
    [MainThread  ] [INFO ] Skipping Custom Plugins directory.
    [MainThread  ] [INFO ] Completed Plugin Loading.
    [MainThread  ] [DEBUG] Loading saved MsgTrack object.
    [RX_MSG      ] [INFO ] Starting
    [TX_MSG      ] [INFO ] Starting
    [MainThread  ] [DEBUG] KeepAlive  Tracker(0): {}
    [RX_MSG      ] [INFO ] Creating aprslib client
    [RX_MSG      ] [INFO ] Attempting connection to noam.aprs2.net:14580
    [RX_MSG      ] [INFO ] Connected to ('198.50.198.139', 14580)
    [RX_MSG      ] [DEBUG] Banner: # aprsc 2.1.8-gf8824e8
    [RX_MSG      ] [INFO ] Sending login information
    [RX_MSG      ] [DEBUG] Server: # logresp KM6XXX-14 verified, server T2VAN
    [RX_MSG      ] [INFO ] Login successful
    [RX_MSG      ] [DEBUG] Logging in to APRS-IS with user 'KM6XXX-14'


.. include:: links.rst
