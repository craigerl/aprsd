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
    #callsign = <None>

    # Enable saving of watch list, packet tracker between restarts.
    # (boolean value)
    #enable_save = true

    # Save location for packet tracking files. (string value)
    #save_location = ~/.config/aprsd

    # Enable code tracing (boolean value)
    #trace_enabled = false

    # Units for display, imperial or metric (string value)
    #units = imperial

    # Comma separated list of enabled plugins for APRSD.To enable
    # installed external plugins add them here.The full python path to the
    # class name must be used (list value)
    #enabled_plugins = aprsd.plugins.email.EmailPlugin,aprsd.plugins.fortune.FortunePlugin,aprsd.plugins.location.LocationPlugin,aprsd.plugins.ping.PingPlugin,aprsd.plugins.query.QueryPlugin,aprsd.plugins.time.TimePlugin,aprsd.plugins.weather.OWMWeatherPlugin,aprsd.plugins.version.VersionPlugin


    [admin]

    #
    # From aprsd.conf
    #

    # Enable the Admin Web Interface (boolean value)
    #web_enabled = false

    # The ip address to listen on (IP address value)
    #web_ip = 0.0.0.0

    # The port to listen on (port value)
    # Minimum value: 0
    # Maximum value: 65535
    #web_port = 8001

    # The admin user for the admin web interface (string value)
    #user = admin

    # Admin interface password (string value)
    #password = <None>


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

    # The APRS-IS hostname (hostname value)
    #host = noam.aprs2.net

    # APRS-IS port (port value)
    # Minimum value: 0
    # Maximum value: 65535
    #port = 14580


    [aprsd_weewx_plugin]

    #
    # From aprsd_weewx_plugin.conf
    #

    # Latitude of the station you want to report as (floating point value)
    #latitude = <None>

    # Longitude of the station you want to report as (floating point
    # value)
    #longitude = <None>

    # How long (in seconds) in between weather reports (integer value)
    #report_interval = 60


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


    [email_plugin]

    #
    # From aprsd.conf
    #

    # (Required) Callsign to validate for doing email commands.Only this
    # callsign can check email. This is also where the email notifications
    # for new emails will be sent. (string value)
    #callsign = <None>

    # Enable the Email plugin? (boolean value)
    #enabled = false

    # Enable the Email plugin Debugging? (boolean value)
    #debug = false

    # Login username/email for IMAP server (string value)
    #imap_login = <None>

    # Login password for IMAP server (string value)
    #imap_password = <None>

    # Hostname/IP of the IMAP server (hostname value)
    #imap_host = <None>

    # Port to use for IMAP server (port value)
    # Minimum value: 0
    # Maximum value: 65535
    #imap_port = 993

    # Use SSL for connection to IMAP Server (boolean value)
    #imap_use_ssl = true

    # Login username/email for SMTP server (string value)
    #smtp_login = <None>

    # Login password for SMTP server (string value)
    #smtp_password = <None>

    # Hostname/IP of the SMTP server (hostname value)
    #smtp_host = <None>

    # Port to use for SMTP server (port value)
    # Minimum value: 0
    # Maximum value: 65535
    #smtp_port = 465

    # Use SSL for connection to SMTP Server (boolean value)
    #smtp_use_ssl = true

    # List of email shortcuts for checking/sending email For Exmaple:
    # wb=walt@walt.com,cl=cl@cl.com
    # Means use 'wb' to send an email to walt@walt.com (list value)
    #email_shortcuts = <None>


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


    [kiss_tcp]

    #
    # From aprsd.conf
    #

    # Enable Serial KISS interface connection. (boolean value)
    #enabled = false

    # The KISS TCP Host to connect to. (hostname value)
    #host = <None>

    # The KISS TCP/IP network port (port value)
    # Minimum value: 0
    # Maximum value: 65535
    #port = 8001


    [logging]

    #
    # From aprsd.conf
    #

    # Date format for log entries (string value)
    #date_format = %m/%d/%Y %I:%M:%S %p

    # Enable Rich logging (boolean value)
    #rich_logging = true

    # File to log to (string value)
    #logfile = <None>

    # Log file format, unless rich_logging enabled. (string value)
    #logformat = [%(asctime)s] [%(threadName)-20.20s] [%(levelname)-5.5s] %(message)s - [%(pathname)s:%(lineno)d]


    [owm_weather_plugin]

    #
    # From aprsd.conf
    #

    # OWMWeatherPlugin api key to OpenWeatherMap's API.This plugin uses
    # the openweathermap API to fetchlocation and weather information.To
    # use this plugin you need to get an openweathermapaccount and
    # apikey.https://home.openweathermap.org/api_keys (string value)
    #apiKey = <None>


    [query_plugin]

    #
    # From aprsd.conf
    #

    # The Ham callsign to allow access to the query plugin from RF.
    # (string value)
    #callsign = <None>


    [rpc_settings]

    #
    # From aprsd.conf
    #

    # Enable RPC calls (boolean value)
    #enabled = true

    # The ip address to listen on (string value)
    #ip = localhost

    # The port to listen on (port value)
    # Minimum value: 0
    # Maximum value: 65535
    #port = 18861

    # Magic word to authenticate requests between client/server (string
    # value)
    #magic_word = CHANGEME!!!


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
