# APRSD - Ham radio APRS-IS Message platform software

## KM6LYW and WB4BOR

[![pypi](https://badge.fury.io/py/aprsd.svg)](https://badge.fury.io/py/aprsd)
[![versions](https://img.shields.io/pypi/pyversions/aprsd.svg)](https://pypi.org/pypi/aprsd)
[![slack](https://img.shields.io/badge/slack-@hemna/aprsd-blue.svg?logo=slack)](https://hemna.slack.com/app_redirect?channel=C01KQSCP5RP)
![issues](https://img.shields.io/github/issues/craigerl/aprsd)
![commit](https://img.shields.io/github/last-commit/craigerl/aprsd)
[![imports](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://timothycrosley.github.io/isort/)
[![down](https://static.pepy.tech/personalized-badge/aprsd?period=month&units=international_system&left_color=black&right_color=orange&left_text=Downloads)](https://pepy.tech/project/aprsd)

[APRSD](http://github.com/craigerl/aprsd) is a Ham radio
[APRS](http://aprs.org) message platform built with python.

![image](./aprsd_logo.png)

# Table of Contents

1. [APRSD - Ham radio APRS-IS Message platform software](#aprsd---ham-radio-aprs-is-message-platform-software)
2. [What is APRSD](#what-is-aprsd)
3. [APRSD Plugins/Extensions](#aprsd-pluginsextensions)
4. [List of existing plugins - APRS Message processing/responders](#list-of-existing-plugins---aprs-message-processingresponders)
5. [List of existing extensions - Add new capabilities to APRSD](#list-of-existing-extensions---add-new-capabilities-to-aprsd)
6. [APRSD Overview Diagram](#aprsd-overview-diagram)
7. [Typical use case](#typical-use-case)
8. [Installation](#installation)
9. [Example usage](#example-usage)
10. [Help](#help)
11. [Commands](#commands)
12. [Configuration](#configuration)
13. [server](#server)
14. [Current list plugins](#current-list-plugins)
15. [Current list extensions](#current-list-extensions)
16. [send-message](#send-message)
17. [Development](#development)
18. [Release](#release)
19. [Building your own APRSD plugins](#building-your-own-aprsd-plugins)
20. [Docker Container](#docker-container)
21. [Running the container](#running-the-container)
22. [Activity](#activity)
23. [Star History](#star-history)

---

> [!WARNING]
> Legal operation of this software requires an amateur radio license and a valid call sign.

> [!NOTE]
> Star this repo to follow our progress! This code is under active development, and contributions are both welcomed and appreciated. See [CONTRIBUTING.md](<https://github.com/craigerl/aprsd/blob/master/CONTRIBUTING.md>) for details.

### What is APRSD

APRSD is a python application for interacting with the APRS network and Ham radios with KISS interfaces and
providing APRS services for HAM radio operators.

APRSD currently has the following commands to use.

 -  server - Start the aprsd server gateway process.
 -  listen - Listen to packets on the APRS-IS Network based on FILTER.
 -  send-message - Send a message to a callsign via APRS_IS.
 -  check-version - Check this version against the latest in pypi.org.
 -  completion - Show the shell completion code
 -  dev - Development type subcommands
 -  dump-stats - Dump the current stats from the running APRSD instance.
 -  export-config - Export all config options from installed APRSD plugins...
 -  export-plugins - Export all installed APRSD plugins as JSON.
 -  fetch-stats - Fetch stats from a APRSD admin web interface.
 -  healthcheck - Check the health of the running aprsd server.
 -  json-config - Output the current loaded configuration in JSON format.
 -  list-extensions - List the built in extensions available to APRSD.
 -  list-plugins - List the built in plugins available to APRSD.
 -  passcode - Generate an APRS passcode for a callsign.
 -  sample-config - Generate a sample Config file from aprsd and all...
 -  version - Show the APRSD version.

Each of those commands can connect to the APRS-IS network if internet
connectivity is available. If internet is not available, then APRS can
be configured to talk to a TCP KISS TNC for radio connectivity directly.

Please [read the docs](https://aprsd.readthedocs.io) to learn more!

[![asciicast](https://asciinema.org/a/etTzphsf26aEZWrK8iKvU5Ekp.svg)](https://asciinema.org/a/etTzphsf26aEZWrK8iKvU5Ekp)

### APRSD Plugins/Extensions

APRSD Has the ability to add plugins and extensions.  Plugins add new message filters that can look for specific messages and respond.  For example, the aprsd-email-plugin adds the ability to send/recieve email to/from an APRS callsign.  Extensions add new unique capabilities to APRSD itself.  For example the aprsd-admin-extension adds a web interface command that shows the running status of the aprsd server command.  aprsd-webchat-extension is a new web based APRS 'chat' command.

You can see the [available plugins/extensions on pypi here:](https://pypi.org/search/?q=aprsd) [https://pypi.org/search/?q=aprsd](https://pypi.org/search/?q=aprsd)

> [!NOTE]
> aprsd admin and webchat commands have been extracted into separate extensions.
 * [See admin extension here](https://github.com/hemna/aprsd-admin-extension) <div id="admin logo" align="left"><img src="https://raw.githubusercontent.com/hemna/aprsd-admin-extension/refs/heads/master/screenshot.png" alt="Web Admin" width="340"/></div>

 * [See webchat extension here](https://github.com/hemna/aprsd-webchat-extension) <div id="webchat logo" align="left"><img src="https://raw.githubusercontent.com/hemna/aprsd-webchat-extension/master/screenshot.png" alt="Webchat" width="340"/></div>

 * [See CLI chat extension here](https://github.com/hemna/aprsd-rich-cli-extension) <div id="rich_logo" align="left"><img src="https://raw.githubusercontent.com/hemna/aprsd-rich-cli-extension/refs/heads/master/screenshot.png" alt="CLI Chat" width="340"></div>

### List of existing plugins - APRS Message processing/responders

 - [aprsd-email-plugin](https://github.com/hemna/aprsd-email-plugin) - send/receive email!
 - [aprsd-location-plugin](https://github.com/hemna/aprsd-location-plugin) - get latest GPS location.
 - [aprsd-locationdata-plugin](https://github.com/hemna/aprsd-locationdata-plugin) - get latest GPS location
 - [aprsd-digipi-plugin](https://github.com/hemna/aprsd-digipi-plugin) - Look for digipi beacon packets
 - [aprsd-w3w-plugin](https://github.com/hemna/aprsd-w3w-plugin) - get your w3w coordinates
 - [aprsd-mqtt-plugin](https://github.com/hemna/aprsd-mqtt-plugin) - send aprs packets to an MQTT topic
 - [aprsd-telegram-plugin](https://github.com/hemna/aprsd-telegram-plugin) - send/receive messages to telegram
 - [aprsd-borat-plugin](https://github.com/hemna/aprsd-borat-plugin) - get Borat quotes
 - [aprsd-wxnow-plugin](https://github.com/hemna/aprsd-wxnow-plugin) - get closest N weather station reports
 - [aprsd-weewx-plugin](https://github.com/hemna/aprsd-weewx-plugin) - get weather from your weewx weather station
 - [aprsd-slack-plugin](https://github.com/hemna/aprsd-slack-plugin) - send/receive messages to a slack channel
 - [aprsd-sentry-plugin](https://github.com/hemna/aprsd-sentry-plugin) -
 - [aprsd-repeat-plugins](https://github.com/hemna/aprsd-repeat-plugins) - plugins for the REPEAT service. Get nearest Ham radio repeaters!
 - [aprsd-twitter-plugin](https://github.com/hemna/aprsd-twitter-plugin) - make tweets from your Ham Radio!
 - [aprsd-timeopencage-plugin](https://github.com/hemna/aprsd-timeopencage-plugin) - Get local time for a callsign
 - [aprsd-stock-plugin](https://github.com/hemna/aprsd-stock-plugin) - get stock quotes from your Ham radio

### List of existing extensions - Add new capabilities to APRSD

 - [aprsd-admin-extension](https://github.com/hemna/aprsd-admin-extension) - Web Administration page for APRSD
 - [aprsd-webchat-extension](https://github.com/hemna/aprsd-webchat-extension) - Web page for APRS Messaging
 - [aprsd-rich-cli-extension](https://github.com/hemna/aprsd-rich-cli-extension) - Textual rich CLI versions of aprsd commands
 - [aprsd-irc-extension](https://github.com/hemna/aprsd-irc-extension) - an IRC like server command for APRS

### APRSD Overview Diagram

![image](https://raw.githubusercontent.com/craigerl/aprsd/master/docs/_static/aprsd_overview.svg?sanitize=true)

### Typical use case

APRSD\'s typical use case is that of providing an APRS wide service to
all HAM radio operators. For example the callsign \'REPEAT\' on the APRS
network is actually an instance of APRSD that can provide a list of HAM
repeaters in the area of the callsign that sent the message.

Ham radio operator using an APRS enabled HAM radio sends a message to
check the weather. An APRS message is sent, and then picked up by APRSD.
The APRS packet is decoded, and the message is sent through the list of
plugins for processing. For example, the WeatherPlugin picks up the
message, fetches the weather for the area around the user who sent the
request, and then responds with the weather conditions in that area.
Also includes a watch list of HAM callsigns to look out for. The watch
list can notify you when a HAM callsign in the list is seen and now
available to message on the APRS network.

### Installation

**Install uv (recommended):**

`uv` is a fast Python package installer and resolver. To install `uv`, visit [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

To install `aprsd`, use uv:

`uv pip install aprsd`

Or with the traditional pip:

`pip install aprsd`

### Example usage

`aprsd -h`

### Help

:

    └─> aprsd -h
    Usage: aprsd [OPTIONS] COMMAND [ARGS]...

    Options:
      --version   Show the version and exit.
      -h, --help  Show this message and exit.

    Commands:
      check-version    Check this version against the latest in pypi.org.
      completion       Show the shell completion code
      dev              Development type subcommands
      dump-stats       Dump the current stats from the running APRSD instance.
      export-config    Export all config options from installed APRSD plugins...
      export-plugins   Export all installed APRSD plugins as JSON.
      fetch-stats      Fetch stats from a APRSD admin web interface.
      healthcheck      Check the health of the running aprsd server.
      json-config      Output the current loaded configuration in JSON format.
      list-extensions  List the built in extensions available to APRSD.
      list-plugins     List the built in plugins available to APRSD.
      listen           Listen to packets on the APRS-IS Network based on FILTER.
      passcode         Generate an APRS passcode for a callsign.
      sample-config    Generate a sample Config file from aprsd and all...
      send-message     Send a message to a callsign via APRS_IS.
      server           Start the aprsd server gateway process.
      version          Show the APRSD version.

### Commands

### Configuration

This command outputs a sample config yml formatted block that you can
edit and use to pass in to `aprsd` with `-c`. By default aprsd looks in
`~/.config/aprsd/aprsd.yml`

`aprsd sample-config`

    └─> aprsd sample-config
    ...

### server

This is the main server command that will listen to APRS-IS servers and
look for incomming commands to the callsign configured in the config
file

    └─[$] > aprsd server --help
        Usage: aprsd server [OPTIONS]

          Start the aprsd server gateway process.

        Options:
          --loglevel [CRITICAL|ERROR|WARNING|INFO|DEBUG]
                                          The log level to use for aprsd.log
                                          [default: INFO]
          -c, --config TEXT               The aprsd config file to use for options.
                                          [default:
                                          /Users/i530566/.config/aprsd/aprsd.yml]
          --quiet                         Don't log to stdout
          -f, --flush                     Flush out all old aged messages on disk.
                                          [default: False]
          -h, --help                      Show this message and exit.

    └─> aprsd server
    Registering LogMonitorThread
    2025-01-06 16:27:12.398 | MainThread         | INFO     | APRSD is up to date | aprsd.cmds.server:server:82
    2025-01-06 16:27:12.398 | MainThread         | INFO     | APRSD Started version: 4.2.4 | aprsd.cmds.server:server:83
    2025-01-06 16:27:12.398 | MainThread         | INFO     | Creating client connection | aprsd.cmds.server:server:101
    2025-01-06 16:27:12.398 | MainThread         | INFO     | Creating aprslib client(noam.aprs2.net:14580) and logging in WB4BOR-1. | aprsd.client.aprsis:setup_connection:136
    2025-01-06 16:27:12.398 | MainThread         | INFO     | Attempting connection to noam.aprs2.net:14580 | aprslib.inet:_connect:226
    2025-01-06 16:27:12.473 | MainThread         | INFO     | Connected to ('44.135.208.225', 14580) | aprslib.inet:_connect:233
    2025-01-06 16:27:12.617 | MainThread         | INFO     | Login successful | aprsd.client.drivers.aprsis:_send_login:154
    2025-01-06 16:27:12.618 | MainThread         | INFO     | Connected to T2BC | aprsd.client.drivers.aprsis:_send_login:156
    2025-01-06 16:27:12.618 | MainThread         | INFO     | <aprsd.client.aprsis.APRSISClient object at 0x103a36480> | aprsd.cmds.server:server:103
    2025-01-06 16:27:12.618 | MainThread         | INFO     | Loading Plugin Manager and registering plugins | aprsd.cmds.server:server:117
    2025-01-06 16:27:12.619 | MainThread         | INFO     | Loading APRSD Plugins | aprsd.plugin:setup_plugins:492


#### Current list plugins

For detailed documentation of each built-in plugin (commands, configuration, and
troubleshooting), see [PLUGINS.md](PLUGINS.md).

    └─> aprsd list-plugins
                                                        🐍 APRSD Built-in Plugins 🐍
    ┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃ Plugin Name       ┃ Info                                                       ┃ Type         ┃ Plugin Path                             ┃
    ┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
    │ FortunePlugin     │ Give me a fortune                                          │ RegexCommand │ aprsd.plugins.fortune.FortunePlugin     │
    │ NotifySeenPlugin  │ Notify me when a CALLSIGN is recently seen on APRS-IS      │ WatchList    │ aprsd.plugins.notify.NotifySeenPlugin   │
    │ PingPlugin        │ reply with a Pong!                                         │ RegexCommand │ aprsd.plugins.ping.PingPlugin           │
    │ TimePlugin        │ What is the current local time.                            │ RegexCommand │ aprsd.plugins.time.TimePlugin         │
    │ USMetarPlugin     │ USA only METAR of GPS Beacon location                      │ RegexCommand │ aprsd.plugins.weather.USMetarPlugin     │
    │ USWeatherPlugin   │ Provide USA only weather of GPS Beacon location            │ RegexCommand │ aprsd.plugins.weather.USWeatherPlugin   │
    │ VersionPlugin     │ What is the APRSD Version                                  │ RegexCommand │ aprsd.plugins.version.VersionPlugin     │
    └───────────────────┴────────────────────────────────────────────────────────────┴──────────────┴─────────────────────────────────────────┘


                                                    Pypi.org APRSD Installable Plugin Packages

                                                    Install any of the following plugins with
                                                        'uv pip install <Plugin Package Name>'
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
    ┃ Plugin Package Name          ┃ Description                                                  ┃  Version   ┃      Released       ┃ Installed? ┃
    ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
    │ 📂 aprsd-assistant-plugin    │ APRSd plugin for hosting the APRS Assistant chatbot          │   0.0.3    │ 2024-10-20T02:59:39 │     No     │
    │                              │ (aprs-assistant)                                             │            │                     │            │
    │ 📂 aprsd-borat-plugin        │ Borat quotes for aprsd plugin                                │ 0.1.1.dev1 │ 2024-01-19T16:04:38 │     No     │
    │ 📂 aprsd-locationdata-plugin │ Fetch location information from a callsign                   │   0.3.0    │ 2024-02-06T17:20:43 │     No     │
    │ 📂 aprsd-mqtt-plugin         │ APRSD MQTT Plugin sends APRS packets to mqtt queue           │   0.2.0    │ 2023-04-17T16:01:50 │     No     │
    │ 📂 aprsd-repeat-plugins      │ APRSD Plugins for the REPEAT service                         │   1.2.0    │ 2023-01-10T17:15:36 │     No     │
    │ 📂 aprsd-sentry-plugin       │ Ham radio APRSD plugin that does....                         │   0.1.2    │ 2022-12-02T19:07:33 │     No     │
    │ 📂 aprsd-slack-plugin        │ Amateur radio APRS daemon which listens for messages and     │   1.2.0    │ 2023-01-10T19:21:33 │     No     │
    │                              │ responds                                                     │            │                     │            │
    │ 📂 aprsd-stock-plugin        │ Ham Radio APRSD Plugin for fetching stock quotes             │   0.1.3    │ 2022-12-02T18:56:19 │    Yes     │
    │ 📂 aprsd-telegram-plugin     │ Ham Radio APRS APRSD plugin for Telegram IM service          │   0.1.3    │ 2022-12-02T19:07:15 │     No     │
    │ 📂 aprsd-timeopencage-plugin │ APRSD plugin for fetching time based on GPS location         │   0.2.0    │ 2023-01-10T17:07:11 │     No     │
    │ 📂 aprsd-twitter-plugin      │ Python APRSD plugin to send tweets                           │   0.5.0    │ 2023-01-10T16:51:47 │     No     │
    │ 📂 aprsd-weewx-plugin        │ HAM Radio APRSD that reports weather from a weewx weather    │   0.3.2    │ 2023-04-20T20:16:19 │     No     │
    │                              │ station.                                                     │            │                     │            │
    │ 📂 aprsd-wxnow-plugin        │ APRSD Plugin for getting the closest wx reports to last      │   0.2.0    │ 2023-10-08T01:27:29 │    Yes     │
    │                              │ beacon                                                       │            │                     │            │
    └──────────────────────────────┴──────────────────────────────────────────────────────────────┴────────────┴─────────────────────┴────────────┘


                                    🐍 APRSD Installed 3rd party Plugins 🐍
    ┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃ Package Name       ┃ Plugin Name     ┃ Version ┃ Type         ┃ Plugin Path                              ┃
    ┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
    │ aprsd-stock-plugin │ YahooStockQuote │  0.1.3  │ RegexCommand │ aprsd_stock_plugin.stock.YahooStockQuote │
    │ aprsd-wxnow-plugin │ WXNowPlugin     │  0.2.0  │ RegexCommand │ aprsd_wxnow_plugin.conf.opts.WXNowPlugin │
    └────────────────────┴─────────────────┴─────────┴──────────────┴──────────────────────────────────────────┘

#### Current list extensions
    └─> aprsd list-extensions


                                                    Pypi.org APRSD Installable Extension Packages

                                                Install any of the following extensions by running
                                                        'uv pip install <Plugin Package Name>'
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
    ┃ Extension Package Name   ┃ Description                                                         ┃ Version ┃      Released       ┃ Installed? ┃
    ┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
    │ 📂 aprsd-admin-extension │ Administration extension for the Ham radio APRSD Server             │  1.0.1  │ 2025-01-06T21:57:24 │    Yes     │
    │ 📂 aprsd-irc-extension   │ An Extension to Ham radio APRSD Daemon to act like an irc server    │  0.0.5  │ 2024-04-09T11:28:47 │     No     │
    │                          │ for APRS                                                            │         │                     │            │
    │ 📂 aprsd-rich-cli-extens │ APRSD Extension to create textual rich CLI versions of aprsd        │  0.1.1  │ 2024-12-01T00:00:00 │     No     │
    │     ion                  │ commands                                                            │         │                     │            │
    │ 📂 aprsd-webchat-extens  │ Web page for APRS Messaging                                          │  1.2.3  │ 2024-10-01T00:00:00 │     No     │
    │     ion                  │                                                                      │         │                     │            │
    └──────────────────────────┴─────────────────────────────────────────────────────────────────────┴─────────┴─────────────────────┴────────────┘

### send-message

This command is typically used for development to send another aprsd
instance test messages

    └─[$] > aprsd send-message -h
    Usage: aprsd send-message [OPTIONS] TOCALLSIGN COMMAND...

      Send a message to a callsign via APRS_IS.

    Options:
      --loglevel [CRITICAL|ERROR|WARNING|INFO|DEBUG]
                                      The log level to use for aprsd.log
                                      [default: INFO]
      -c, --config TEXT               The aprsd config file to use for options.
                                      [default:
                                      /Users/i530566/.config/aprsd/aprsd.yml]
      --quiet                         Don't log to stdout
      --aprs-login TEXT               What callsign to send the message from.
                                      [env var: APRS_LOGIN]
      --aprs-password TEXT            the APRS-IS password for APRS_LOGIN  [env
                                      var: APRS_PASSWORD]
      -n, --no-ack                    Don't wait for an ack, just sent it to APRS-
                                      IS and bail.  [default: False]
      -w, --wait-response             Wait for a response to the message?
                                      [default: False]
      --raw TEXT                      Send a raw message.  Implies --no-ack
      -h, --help                      Show this message and exit.

### Development

-   `git clone git@github.com:craigerl/aprsd.git`
-   `cd aprsd`
-   `make dev`

#### Workflow

While working aprsd, The workflow is as follows:

-   Checkout a new branch to work on by running

    `git checkout -b mybranch`

-   Make your changes to the code

-   Run Tox with the following options:

    -   `tox -efast8`
    -   `tox -efmt`
    -   `tox -p`

-   Commit your changes. This will run the pre-commit hooks which does
    checks too

    `git commit`

-   Once you are done with all of your commits, then push up the branch
    to github with:

    `git push -u origin mybranch`

-   Create a pull request from your branch so github tests can run and
    we can do a code review.

#### Release

To do release to pypi:

-   Tag release with:

    `git tag -v1.XX -m "New release"`

-   Push release tag:

    `git push origin master --tags`

-   Do a test build and verify build is valid by running:

    `make build`

-   Once twine is happy, upload release to pypi:

    `make upload`

#### Building your own APRSD plugins

For information on building your own APRSD plugins, see the [Plugin Development documentation](https://aprsd.readthedocs.io/en/latest/plugin.html).

### Docker Container

For information on building Docker containers (official and development builds), see the [Docker Container documentation](https://aprsd.readthedocs.io/en/latest/readme.html#docker-container).

### Running the container

There is a `docker-compose.yml` file in the `docker/` directory that can
be used to run your container. To provide the container an `aprsd.conf`
configuration file, change your `docker-compose.yml` as shown below:

    volumes:
        - $HOME/.config/aprsd:/config

To install plugins at container start time, pass in a list of
comma-separated list of plugins on PyPI using the `APRSD_PLUGINS`
environment variable in the `docker-compose.yml` file. Note that version
constraints may also be provided. For example:

    environment:
        - APRSD_PLUGINS=aprsd-slack-plugin>=1.0.2,aprsd-twitter-plugin


### Activity

![Alt](https://repobeats.axiom.co/api/embed/8b96657861770a15f0b851a5eebafb34d0e0b3d3.svg "Repobeats analytics image")

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=craigerl/aprsd&type=Date)](https://star-history.com/#craigerl/aprsd&Date)
