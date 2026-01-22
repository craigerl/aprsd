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

How APRSD processes messages
-----------------------------

When APRSD receives an APRS message packet, it follows a structured processing flow:

1. **Packet Reception**: The ``RX_PKT`` thread receives packets from the APRS-IS network
   and places them into a packet queue.

2. **Packet Processing**: The ``ProcessPKT`` thread processes packets from the queue.
   It determines if the packet is:

   - An ACK packet destined for APRSD (handled separately)
   - A Reject packet (handled separately)
   - A MessagePacket destined for APRSD's callsign
   - Other packet types (beacons, weather, etc.)

3. **Message Routing**: When a MessagePacket is received that is addressed to APRSD's
   callsign, the packet is sent to the ``process_our_message_packet`` method.

4. **Plugin Processing**: The message packet is passed to the PluginManager, which:

   - Iterates through all registered plugins in the order they were configured
   - For each plugin, checks if the message matches the plugin's regex pattern
   - If a match is found, calls the plugin's ``process()`` method with the packet
   - Collects any reply messages returned by the plugins

5. **Response Handling**: Any reply messages returned by plugins are sent back to the
   original sender via the APRS-IS network. Plugins can return:

   - A string message (converted to a MessagePacket)
   - A Packet object (sent as-is)
   - A list of messages (multiple replies)
   - ``NULL_MESSAGE`` (indicates the plugin processed the message but has no reply)

6. **ACK Handling**: After processing, if the message had a message ID, APRSD
   automatically sends an ACK packet to acknowledge receipt.

This plugin-based architecture allows APRSD to be extended with custom functionality
without modifying the core codebase. Each plugin can independently process messages
and respond as needed. See the :doc:`plugin <plugin>` documentation for information
on creating your own plugins.

.. code-block:: shell

    ❯ aprsd server --loglevel DEBUG
    2025-12-10 14:30:05.146 | MainThread         | INFO     | Python version: 3.10.14 (main, Aug 14 2024, 05:14:46) [Clang 18.1.8 ] | aprsd.cmds.server:server:43
    2025-12-10 14:30:05.147 | MainThread         | INFO     | APRSD Started version: 4.2.5.dev8+g9c0695794 | aprsd.cmds.server:server:44
    2025-12-10 14:30:05.147 | MainThread         | INFO     | APRSD is up to date | aprsd.cmds.server:server:49
    2025-12-10 14:30:05.167 | MainThread         | INFO     | Creating aprslib client(155.138.131.1:14580) and logging in WB4BOR-1. try #1 | aprsd.client.drivers.aprsis:setup_connection:103
    2025-12-10 14:30:05.167 | MainThread         | INFO     | Attempting connection to 155.138.131.1:14580 | aprsd.client.drivers.lib.aprslib:_connect:69
    2025-12-10 14:30:05.193 | MainThread         | INFO     | Connected to ('155.138.131.1', 14580) | aprsd.client.drivers.lib.aprslib:_connect:78
    2025-12-10 14:30:05.232 | MainThread         | DEBUG    | Banner: # aprsc 2.1.19-g730c5c0 | aprsd.client.drivers.lib.aprslib:_connect:96
    2025-12-10 14:30:05.232 | MainThread         | DEBUG    | Sending login information | aprsd.client.drivers.lib.aprslib:_send_login:180
    2025-12-10 14:30:05.256 | MainThread         | DEBUG    | Server: '# logresp WB4BOR-1 verified, server T2CAEAST' | aprsd.client.drivers.lib.aprslib:_send_login:190
    2025-12-10 14:30:05.256 | MainThread         | INFO     | Login successful | aprsd.client.drivers.lib.aprslib:_send_login:212
    2025-12-10 14:30:05.256 | MainThread         | INFO     | Connected to T2CAEAST | aprsd.client.drivers.lib.aprslib:_send_login:214
    2025-12-10 14:30:05.256 | MainThread         | INFO     | Creating client connection | aprsd.cmds.server:server:62
    2025-12-10 14:30:05.256 | MainThread         | INFO     | <aprsd.client.client.APRSDClient object at 0x1096ac460> | aprsd.cmds.server:server:64
    2025-12-10 14:30:05.256 | MainThread         | INFO     | Loading Plugin Manager and registering plugins | aprsd.cmds.server:server:78
    2025-12-10 14:30:05.257 | MainThread         | INFO     | Loading APRSD Plugins | aprsd.plugin:setup_plugins:493
    2025-12-10 14:30:05.257 | MainThread         | INFO     | Registering Regex plugin 'aprsd.plugins.weather.USWeatherPlugin'(4.2.5.dev8+g9c0695794) -- ^[wW] | aprsd.plugin:_load_plugin:452
    2025-12-10 14:30:05.257 | MainThread         | INFO     | Completed Plugin Loading. | aprsd.plugin:setup_plugins:513
    2025-12-10 14:30:05.257 | MainThread         | DEBUG    | ******************************************************************************** | oslo_config.cfg:log_opt_values:2804
    2025-12-10 14:30:05.257 | MainThread         | DEBUG    | Configuration options gathered from: | oslo_config.cfg:log_opt_values:2805
    2025-12-10 14:30:05.257 | MainThread         | DEBUG    | command line args: [] | oslo_config.cfg:log_opt_values:2806
    2025-12-10 14:30:05.257 | MainThread         | DEBUG    | config files: ['/Users/I530566/.config/aprsd/aprsd.conf'] | oslo_config.cfg:log_opt_values:2807
    2025-12-10 14:30:05.257 | MainThread         | DEBUG    | ================================================================================ | oslo_config.cfg:log_opt_values:2809
    2025-12-10 14:30:05.257 | MainThread         | DEBUG    | ack_rate_limit_period          = 1 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | beacon_interval                = 60 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | beacon_symbol                  = / | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | callsign                       = WB4BOR-1 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | config_dir                     = [] | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | config_file                    = ['/Users/I530566/.config/aprsd/aprsd.conf'] | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | config_source                  = [] | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | default_ack_send_count         = 3 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | default_packet_send_count      = 3 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | enable_beacon                  = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | enable_packet_logging          = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | enable_save                    = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | enable_seen_list               = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | enable_sending_ack_packets     = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | enabled_plugins                = ['aprsd.plugins.weather.USWeatherPlugin'] | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | is_digipi                      = False | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | latitude                       = 37.3443862 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | load_help_plugin               = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | log_packet_format              = compact | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | longitude                      = -78.850000 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | msg_rate_limit_period          = 2 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.258 | MainThread         | DEBUG    | packet_dupe_timeout            = 300 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | packet_list_maxlen             = 5000 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | packet_list_stats_maxlen       = 20 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | save_location                  = /Users/I530566/.config/aprsd/ | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | shell_completion               = None | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | trace_enabled                  = False | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | units                          = imperial | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | logging.enable_color           = True | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | logging.enable_console_stdout  = True | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | logging.log_level              = INFO | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | logging.logfile                = /tmp/aprsd.log | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | logging.logformat              = <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <yellow>{thread.name: <18}</yellow> | <level>{level: <8}</level> | <level>{message}</level> | <cyan>{name}</cyan>:<cyan>{function:}</cyan>:<magenta>{line:}</magenta> | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | watch_list.alert_callsign      = WB4BOR-1 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | watch_list.alert_time_seconds  = 3600 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | watch_list.callsigns           = ['APPOMX', 'REPEAT', 'KM6LYW', 'WB4BOR', 'M0IAX', 'VE3SCN', 'WA4RTS-5', 'KC9BUH', 'W4SOU-7', 'KD9KAF-7', 'NN4RB-9', 'KN4MLN-9', 'KK4WZS-8', 'K2VIZ-1', 'KE3XE-9', 'WB2UTI-9', 'KO4ARL-7', 'LMS6CAE42', 'WDJ6895', 'PHISVR', 'F1BIS-9', 'M7APR-9', 'Y09INA-5', 'M0PLT-7', 'M0GLJ-14', 'MW6JUY-10', 'M0XZS', 'M0HPP-8', 'ON2BBW-8'] | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | watch_list.enabled             = True | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | watch_list.packet_keep_count   = 10 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | aprs_registry.description      = None | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | aprs_registry.enabled          = False | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | aprs_registry.frequency_seconds = 3600 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | aprs_registry.registry_url     = https://aprs.hemna.com/api/v1/registry | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | aprs_registry.service_website  = None | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.259 | MainThread         | DEBUG    | aprs_network.enabled           = True | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | aprs_network.host              = 155.138.131.1 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | aprs_network.password          = **** | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | aprs_network.port              = 14580 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | kiss_serial.baudrate           = 9600 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | kiss_serial.device             = None | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | kiss_serial.enabled            = False | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | kiss_serial.path               = ['WIDE1-1', 'WIDE2-1'] | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | kiss_tcp.enabled               = False | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | kiss_tcp.host                  = None | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | kiss_tcp.path                  = ['WIDE1-1', 'WIDE2-1'] | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | kiss_tcp.port                  = 8001 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | fake_client.enabled            = False | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | aprs_fi.apiKey                 = 152327.lds79D1bgvlbd | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | owm_weather_plugin.apiKey      = e26b403324563f24a290fa1d06459bae | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | avwx_plugin.apiKey             = Foo | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | avwx_plugin.base_url            = https://avwx.rest | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | ******************************************************************************** | oslo_config.cfg:log_opt_values:2828
    2025-12-10 14:30:05.260 | MainThread         | INFO     | Message Plugins enabled and running: | aprsd.cmds.server:server:86
    2025-12-10 14:30:05.260 | MainThread         | INFO     | <aprsd.plugins.weather.USWeatherPlugin object at 0x109a74c40> | aprsd.cmds.server:server:88
    2025-12-10 14:30:05.260 | MainThread         | INFO     | <aprsd.plugin.HelpPlugin object at 0x109a74ac0> | aprsd.cmds.server:server:88
    2025-12-10 14:30:05.260 | MainThread         | INFO     | Watchlist Plugins enabled and running: | aprsd.cmds.server:server:89
    2025-12-10 14:30:05.260 | MainThread         | DEBUG    | Loading saved packet tracking data. | aprsd.cmds.server:server:103
    2025-12-10 14:30:05.261 | MainThread         | DEBUG    | PacketList::No save file found. | aprsd.utils.objectstore:load:113
    2025-12-10 14:30:05.261 | MainThread         | DEBUG    | SeenList::No save file found. | aprsd.utils.objectstore:load:113
    2025-12-10 14:30:05.261 | MainThread         | DEBUG    | PacketTrack::No save file found. | aprsd.utils.objectstore:load:113
    2025-12-10 14:30:05.262 | MainThread         | DEBUG    | WatchList::Loaded 29 entries from disk. | aprsd.utils.objectstore:load:103
    2025-12-10 14:30:05.262 | MainThread         | INFO     | Beacon Enabled.  Starting Beacon thread. | aprsd.cmds.server:server:122
    2025-12-10 14:30:05.262 | MainThread         | INFO     | Beacon thread is running and will send beacons every 60 seconds. | aprsd.threads.tx:__init__:253
    2025-12-10 14:30:05.263 | KeepAlive          | DEBUG    | Starting | aprsd.threads.aprsd:run:64
    2025-12-10 14:30:05.263 | StatsStore         | DEBUG    | Starting | aprsd.threads.aprsd:run:64
    2025-12-10 14:30:05.263 | RX_PKT             | DEBUG    | Starting | aprsd.threads.aprsd:run:64
    2025-12-10 14:30:05.264 | ProcessPKT         | DEBUG    | Starting | aprsd.threads.aprsd:run:64
    2025-12-10 14:30:05.264 | BeaconSendThread   | DEBUG    | Starting | aprsd.threads.aprsd:run:64


.. include:: links.rst
