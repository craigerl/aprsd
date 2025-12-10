APRSD Configure
===============

Configure APRSD
------------------------

Once APRSD is :doc:`installed <install>` You will need to configure the config file
for running.


Generate config file
---------------------
If you have never run the server, running it the first time will generate
a sample config file in the default location of ~/.config/aprsd/aprsd.yml

.. code-block:: shell

    └─> aprsd server
    12/28/2022 04:26:31 PM MainThread           ERROR    No config file found!! run 'aprsd sample-config'                             cli_helper.py:90
    12/28/2022 04:26:31 PM MainThread           ERROR    Config aprs_network.password not set.                                           client.py:105
    12/28/2022 04:26:31 PM MainThread           ERROR    Option 'aprs_network.password is not set.' was not in config file               client.py:268
    12/28/2022 04:26:31 PM MainThread           ERROR    APRS client is not properly configured in config file.                           server.py:58

You can see the sample config file output

Sample config file
------------------

.. code-block:: shell

    └─> aprsd sample-config
    [DEFAULT]

    #
    # From aprsd.conf
    #

    # Callsign to use for messages sent by APRSD (string value)
    #callsign = NOCALL

    # Enable saving of watch list, packet tracker between restarts.
    # (boolean value)
    #enable_save = true

    # Save location for packet tracking files. (string value)
    #save_location = /Users/I530566/.config/aprsd/

    # Enable code tracing (boolean value)
    #trace_enabled = false

    # Units for display, imperial or metric (string value)
    #units = imperial

    # The wait period in seconds per Ack packet being sent.1 means 1 ack
    # packet per second allowed.2 means 1 pack packet every 2 seconds
    # allowed (integer value)
    #ack_rate_limit_period = 1

    # Wait period in seconds per non AckPacket being sent.2 means 1 packet
    # every 2 seconds allowed.5 means 1 pack packet every 5 seconds
    # allowed (integer value)
    #msg_rate_limit_period = 2

    # The number of seconds before a packet is not considered a duplicate.
    # (integer value)
    #packet_dupe_timeout = 300

    # Enable sending of a GPS Beacon packet to locate this service.
    # Requires latitude and longitude to be set. (boolean value)
    #enable_beacon = false

    # The number of seconds between beacon packets. (integer value)
    #beacon_interval = 1800

    # The symbol to use for the GPS Beacon packet. See:
    # http://www.aprs.net/vm/DOS/SYMBOLS.HTM (string value)
    #beacon_symbol = /

    # Latitude for the GPS Beacon button.  If not set, the button will not
    # be enabled. (string value)
    #latitude = <None>

    # Longitude for the GPS Beacon button.  If not set, the button will
    # not be enabled. (string value)
    #longitude = <None>

    # When logging packets 'compact' will use a single line formatted for
    # each packet.'multiline' will use multiple lines for each packet and
    # is the traditional format.both will log both compact and multiline.
    # (string value)
    # Possible values:
    # compact - <No description provided>
    # multiline - <No description provided>
    # both - <No description provided>
    #log_packet_format = compact

    # The number of times to send a non ack packet before giving up.
    # (integer value)
    #default_packet_send_count = 3

    # The number of times to send an ack packet in response to recieving a
    # packet. (integer value)
    #default_ack_send_count = 3

    # The maximum number of packets to store in the packet list. (integer
    # value)
    #packet_list_maxlen = 100

    # The maximum number of packets to send in the stats dict for admin
    # ui. -1 means no max. (integer value)
    #packet_list_stats_maxlen = 20

    # Enable the Callsign seen list tracking feature.  This allows aprsd
    # to keep track of callsigns that have been seen and when they were
    # last seen. (boolean value)
    #enable_seen_list = true

    # Set this to False, to disable logging of packets to the log file.
    # (boolean value)
    #enable_packet_logging = true

    # Set this to False to disable the help plugin. (boolean value)
    #load_help_plugin = true

    # Set this to False, to disable sending of ack packets. This will
    # entirely stopAPRSD from sending ack packets. (boolean value)
    #enable_sending_ack_packets = true

    # Set this to True, if APRSD is running on a Digipi.This is useful for
    # changing the behavior of APRSD to work with Digipi. (boolean value)
    #is_digipi = false

    # Comma separated list of enabled plugins for APRSD.To enable
    # installed external plugins add them here.The full python path to the
    # class name must be used (list value)
    #enabled_plugins = aprsd.plugins.fortune.FortunePlugin,aprsd.plugins.location.LocationPlugin,aprsd.plugins.ping.PingPlugin,aprsd.plugins.time.TimePlugin,aprsd.plugins.weather.OWMWeatherPlugin,aprsd.plugins.version.VersionPlugin,aprsd.plugins.notify.NotifySeenPlugin


    [aprs_fi]

    #
    # From aprsd.conf
    #

    # Get the apiKey from your aprs.fi account here:http://aprs.fi/account
    # (string value)
    #apiKey = <None>


    [aprs_network]

    #
    # From aprsd.conf
    #

    # Set enabled to False if there is no internet connectivity.This is
    # useful for a direwolf KISS aprs connection only. (boolean value)
    #enabled = true

    # APRS Username (string value)
    #login = NOCALL

    # APRS Password Get the passcode for your callsign here:
    # https://apps.magicbug.co.uk/passcode (string value)
    #password = <None>

    # The APRS-IS hostname (host address value)
    #host = noam.aprs2.net

    # APRS-IS port (port value)
    # Minimum value: 0
    # Maximum value: 65535
    #port = 14580


    [aprs_registry]

    #
    # From aprsd.conf
    #

    # Enable sending aprs registry information.  This will let the APRS
    # registry know about your service and it's uptime.  No personal
    # information is sent, just the callsign, uptime and description. The
    # service callsign is the callsign set in [DEFAULT] section. (boolean
    # value)
    #enabled = false

    # Description of the service to send to the APRS registry. This is
    # what will show up in the APRS registry.If not set, the description
    # will be the same as the callsign. (string value)
    #description = <None>

    # The APRS registry domain name to send the information to. (string
    # value)
    #registry_url = https://aprs.hemna.com/api/v1/registry

    # The website for your APRS service to send to the APRS registry.
    # (string value)
    #service_website = <None>

    # The frequency in seconds to send the APRS registry information.
    # (integer value)
    #frequency_seconds = 3600


    [avwx_plugin]

    #
    # From aprsd.conf
    #

    # avwx-api is an opensource project that hasa hosted service here:
    # https://avwx.rest/You can launch your own avwx-api in a containerby
    # cloning the githug repo here:https://github.com/avwx-rest/AVWX-API
    # (string value)
    #apiKey = <None>

    # The base url for the avwx API.  If you are hosting your ownHere is
    # where you change the url to point to yours. (string value)
    #base_url = https://avwx.rest


    [fake_client]

    #
    # From aprsd.conf
    #

    # Enable fake client connection. (boolean value)
    #enabled = false


    [kiss_serial]

    #
    # From aprsd.conf
    #

    # Enable Serial KISS interface connection. (boolean value)
    #enabled = false

    # Serial Device file to use.  /dev/ttyS0 (string value)
    #device = <None>

    # The Serial device baud rate for communication (integer value)
    #baudrate = 9600

    # The APRS path to use for wide area coverage. (list value)
    #path = WIDE1-1,WIDE2-1


    [kiss_tcp]

    #
    # From aprsd.conf
    #

    # Enable Serial KISS interface connection. (boolean value)
    #enabled = false

    # The KISS TCP Host to connect to. (host address value)
    #host = <None>

    # The KISS TCP/IP network port (port value)
    # Minimum value: 0
    # Maximum value: 65535
    #port = 8001

    # The APRS path to use for wide area coverage. (list value)
    #path = WIDE1-1,WIDE2-1


    [logging]

    #
    # From aprsd.conf
    #

    # File to log to (string value)
    #logfile = <None>

    # Log file format, unless rich_logging enabled. (string value)
    #logformat = <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <yellow>{thread.name: <18}</yellow> | <level>{level: <8}</level> | <level>{message}</level> | <cyan>{name}</cyan>:<cyan>{function:}</cyan>:<magenta>{line:}</magenta>

    # Log level for logging of events. (string value)
    # Possible values:
    # CRITICAL - <No description provided>
    # ERROR - <No description provided>
    # WARNING - <No description provided>
    # INFO - <No description provided>
    # DEBUG - <No description provided>
    #log_level = INFO

    # Enable ANSI color codes in logging (boolean value)
    #enable_color = true

    # Enable logging to the console/stdout. (boolean value)
    #enable_console_stdout = true


    [owm_weather_plugin]

    #
    # From aprsd.conf
    #

    # OWMWeatherPlugin api key to OpenWeatherMap's API.This plugin uses
    # the openweathermap API to fetchlocation and weather information.To
    # use this plugin you need to get an openweathermapaccount and
    # apikey.https://home.openweathermap.org/api_keys (string value)
    #apiKey = <None>


    [watch_list]

    #
    # From aprsd.conf
    #

    # Enable the watch list feature.  Still have to enable the correct
    # plugin.  Built-in plugin to use is aprsd.plugins.notify.NotifyPlugin
    # (boolean value)
    #enabled = false

    # Callsigns to watch for messsages (list value)
    #callsigns = <None>

    # The Ham Callsign to send messages to for watch list alerts. (string
    # value)
    #alert_callsign = <None>

    # The number of packets to store. (integer value)
    #packet_keep_count = 10

    # Time to wait before alert is sent on new message for users in
    # callsigns. (integer value)
    #alert_time_seconds = 3600

Note, You must edit the config file and change the ham callsign to your
legal FCC HAM callsign, or aprsd server will not start.

.. include:: links.rst
