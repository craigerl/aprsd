APRSD listen
============

Running the APRSD listen command
---------------------------------

The ``aprsd listen`` command allows you to listen to packets on the APRS-IS Network based on a FILTER.
This is useful for monitoring specific APRS traffic without running the full server.

Once APRSD is :doc:`installed <install>` and :doc:`configured <configure>`, the listen command can be started by running:

.. code-block:: shell

   aprsd listen [FILTER]

The FILTER parameter is optional and follows the APRS-IS filter format. For example, ``m/300`` filters for
messages within 300 miles of your configured location.

Example usage
-------------

.. code-block:: shell

    ❯ aprsd listen --loglevel DEBUG m/300
    2025-12-10 14:32:33.813 | MainThread         | INFO     | Python version: 3.10.14 (main, Aug 14 2024, 05:14:46) [Clang 18.1.8 ] | aprsd.cmds.listen:listen:224
    2025-12-10 14:32:33.813 | MainThread         | INFO     | APRSD Listen Started version: 4.2.5.dev8+g9c0695794 | aprsd.cmds.listen:listen:225
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | ******************************************************************************** | oslo_config.cfg:log_opt_values:2804
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | Configuration options gathered from: | oslo_config.cfg:log_opt_values:2805
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | command line args: [] | oslo_config.cfg:log_opt_values:2806
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | config files: ['/Users/I530566/.config/aprsd/aprsd.conf'] | oslo_config.cfg:log_opt_values:2807
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | ================================================================================ | oslo_config.cfg:log_opt_values:2809
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | ack_rate_limit_period          = 1 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | beacon_interval                = 60 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | beacon_symbol                  = / | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | callsign                       = WB4BOR-1 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | config_dir                     = [] | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | config_file                    = ['/Users/I530566/.config/aprsd/aprsd.conf'] | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | config_source                  = [] | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | default_ack_send_count         = 3 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | default_packet_send_count      = 3 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | enable_beacon                  = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | enable_packet_logging          = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.841 | MainThread         | DEBUG    | enable_save                    = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | enable_seen_list               = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | enable_sending_ack_packets     = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | enabled_plugins                = ['aprsd.plugins.weather.AVWXWeatherPlugin'] | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | is_digipi                      = False | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | latitude                       = 37.3443862 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | load_help_plugin               = True | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | log_packet_format              = compact | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | longitude                      = -78.850000 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | msg_rate_limit_period          = 2 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | packet_dupe_timeout            = 300 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | packet_list_maxlen             = 5000 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | packet_list_stats_maxlen       = 20 | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | save_location                  = /Users/I530566/.config/aprsd/ | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | shell_completion               = None | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | trace_enabled                  = False | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | units                          = imperial | oslo_config.cfg:log_opt_values:2817
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | logging.enable_color           = True | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | logging.enable_console_stdout  = True | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | logging.log_level              = INFO | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | logging.logfile                = /tmp/aprsd.log | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | logging.logformat              = <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <yellow>{thread.name: <18}</yellow> | <level>{level: <8}</level> | <level>{message}</level> | <cyan>{name}</cyan>:<cyan>{function:}</cyan>:<magenta>{line:}</magenta> | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | watch_list.alert_callsign      = WB4BOR-1 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | watch_list.alert_time_seconds  = 3600 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | watch_list.callsigns           = ['APPOMX', 'REPEAT', 'KM6LYW', 'WB4BOR', 'M0IAX', 'VE3SCN', 'WA4RTS-5', 'KC9BUH', 'W4SOU-7', 'KD9KAF-7', 'NN4RB-9', 'KN4MLN-9', 'KK4WZS-8', 'K2VIZ-1', 'KE3XE-9', 'WB2UTI-9', 'KO4ARL-7', 'LMS6CAE42', 'WDJ6895', 'PHISVR', 'F1BIS-9', 'M7APR-9', 'Y09INA-5', 'M0PLT-7', 'M0GLJ-14', 'MW6JUY-10', 'M0XZS', 'M0HPP-8', 'ON2BBW-8'] | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | watch_list.enabled             = True | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | watch_list.packet_keep_count   = 10 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | aprs_registry.description      = None | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | aprs_registry.enabled          = False | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.842 | MainThread         | DEBUG    | aprs_registry.frequency_seconds = 3600 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | aprs_registry.registry_url     = https://aprs.hemna.com/api/v1/registry | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | aprs_registry.service_website  = None | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | aprs_network.enabled           = True | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | aprs_network.host              = 155.138.131.1 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | aprs_network.login             = WB4BOR-1 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | aprs_network.password          = **** | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | aprs_network.port              = 14580 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | kiss_serial.baudrate           = 9600 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | kiss_serial.device             = None | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | kiss_serial.enabled            = False | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | kiss_serial.path               = ['WIDE1-1', 'WIDE2-1'] | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | kiss_tcp.enabled               = False | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | kiss_tcp.host                  = None | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | kiss_tcp.path                  = ['WIDE1-1', 'WIDE2-1'] | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | kiss_tcp.port                  = 8001 | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | fake_client.enabled            = False | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | aprs_fi.apiKey                 = 152327.lds79D1bgvlbd | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | owm_weather_plugin.apiKey      = e26b403324563f24a290fa1d06459bae | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | avwx_plugin.apiKey             = Foo | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | avwx_plugin.base_url           = https://avwx.rest | oslo_config.cfg:log_opt_values:2824
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | ******************************************************************************** | oslo_config.cfg:log_opt_values:2828
    2025-12-10 14:32:33.843 | MainThread         | DEBUG    | Loading saved MsgTrack object. | aprsd.cmds.listen:listen:232
    2025-12-10 14:32:33.843 | MainThread         | INFO     | Creating aprslib client(155.138.131.1:14580) and logging in WB4BOR-1. try #1 | aprsd.client.drivers.aprsis:setup_connection:103
    2025-12-10 14:32:33.843 | MainThread         | INFO     | Attempting connection to 155.138.131.1:14580 | aprsd.client.drivers.lib.aprslib:_connect:69
    2025-12-10 14:32:33.869 | MainThread         | INFO     | Connected to ('155.138.131.1', 14580) | aprsd.client.drivers.lib.aprslib:_connect:78
    2025-12-10 14:32:33.900 | MainThread         | DEBUG    | Banner: # aprsc 2.1.19-g730c5c0 | aprsd.client.drivers.lib.aprslib:_connect:96
    2025-12-10 14:32:33.900 | MainThread         | DEBUG    | Sending login information | aprsd.client.drivers.lib.aprslib:_send_login:180
    2025-12-10 14:32:33.924 | MainThread         | DEBUG    | Server: '# logresp WB4BOR-1 verified, server T2CAEAST' | aprsd.client.drivers.lib.aprslib:_send_login:190
    2025-12-10 14:32:33.924 | MainThread         | INFO     | Login successful | aprsd.client.drivers.lib.aprslib:_send_login:212
    2025-12-10 14:32:33.924 | MainThread         | INFO     | Connected to T2CAEAST | aprsd.client.drivers.lib.aprslib:_send_login:214
    2025-12-10 14:32:33.924 | MainThread         | INFO     | Creating client connection | aprsd.cmds.listen:listen:242
    2025-12-10 14:32:33.924 | MainThread         | INFO     | <aprsd.client.client.APRSDClient object at 0x10bd9bfa0> | aprsd.cmds.listen:listen:244
    2025-12-10 14:32:33.924 | MainThread         | DEBUG    | Filter messages on aprsis server by '('m/300',)' | aprsd.cmds.listen:listen:252
    2025-12-10 14:32:33.924 | MainThread         | INFO     | Setting filter to: ('m/300',) | aprslib.inet:set_filter:83
    2025-12-10 14:32:33.925 | MainThread         | INFO     | No packet filtering enabled. | aprsd.cmds.listen:listen:268
    2025-12-10 14:32:33.925 | MainThread         | WARNING  | Not Loading any plugins use --load-plugins to load what's defined in the config file. | aprsd.cmds.listen:listen:282
    2025-12-10 14:32:33.925 | StatsStore         | DEBUG    | Starting | aprsd.threads.aprsd:run:64
    2025-12-10 14:32:33.925 | MainThread         | DEBUG    | Start APRSDRxThread | aprsd.cmds.listen:listen:294
    2025-12-10 14:32:33.926 | RX_PKT             | DEBUG    | Starting | aprsd.threads.aprsd:run:64
    2025-12-10 14:32:33.926 | MainThread         | DEBUG    | Create APRSDListenProcessThread | aprsd.cmds.listen:listen:298
    2025-12-10 14:32:33.926 | MainThread         | DEBUG    | Start APRSDListenProcessThread | aprsd.cmds.listen:listen:306
    2025-12-10 14:32:33.926 | ListenProcThread   | DEBUG    | Starting | aprsd.threads.aprsd:run:64
    2025-12-10 14:32:33.926 | KeepAlive          | DEBUG    | Starting | aprsd.threads.aprsd:run:64
    2025-12-10 14:32:33.926 | MainThread         | DEBUG    | keepalive Join | aprsd.cmds.listen:listen:313
    2025-12-10 14:32:34.927 | RX_PKT             | DEBUG    | Server: # filter m/300 active | aprsd.client.drivers.lib.aprslib:consumer:255
    2025-12-10 14:32:34.942 | RX_PKT             | INFO     | RX(1)↓ MicEPacket:None WX4EMC-1 →WIDE1-1→WIDE2-2→qAR→W4VA-13→ S8QQ8S : Lat:38.197 Lon:-77.561 101 mbits  : Northeast@91.78miles | aprsd.packets.log:log:170
    2025-12-10 14:32:34.965 | RX_PKT             | INFO     | RX(2)↓ BeaconPacket:None W4MUP-10 →TCPIP*→qAS→W4MUP→ APMI06 : Lat:36.208 Lon:-80.269 Igate and Digi U=13.3V  : Southwest@111.08miles | aprsd.packets.log:log:170
    2025-12-10 14:32:35.996 | RX_PKT             | INFO     | RX(3)↓ WeatherPacket:None W4MLN-1 →TCPIP*→qAC→T2CAEAST→ APN000 : Temp 009F Humidity 49% Wind 007MPH@261 Pressure 999.7mb Rain 0.01in/24hr  : West-Southwest@157.78miles | aprsd.packets.log:log:170
    2025-12-10 14:32:37.669 | RX_PKT             | INFO     | RX(4)↓ BeaconPacket:None W4GER →TCPIP*→qAC→T2SYDNEY→ APOSB4 : Lat:38.735 Lon:-77.279 SharkRF openSPOT4  : Northeast@128.60miles | aprsd.packets.log:log:170
    2025-12-10 14:32:37.943 | RX_PKT             | INFO     | RX(5)↓ BeaconPacket:None NM5ER-10 →TCPIP*→qAC→T2SYDNEY→ APLRG1 : Lat:36.440 Lon:-81.140 LoRa APRS  : West-Southwest@141.12miles | aprsd.packets.log:log:170

The listen command connects to the APRS-IS network and displays packets matching the specified filter.
In the example above, packets within 300 miles are displayed, showing various packet types including MicEPacket,
BeaconPacket, and WeatherPacket.

Key differences from the server command
----------------------------------------

Unlike the ``aprsd server`` command, the listen command:

- Does not load plugins by default (use ``--load-plugins`` to enable them)
- Does not respond to messages
- Is designed for monitoring and logging APRS traffic
- Supports APRS-IS filter syntax for targeted packet monitoring

.. include:: links.rst
