Built-in APRSD Plugins
======================

APRSD comes with several built-in plugins that provide various functionality out of the box.
These plugins are automatically available when you install APRSD and can be enabled or disabled
through the configuration file.

Message Command Plugins
------------------------

These plugins respond to APRS messages sent to your APRSD callsign.

PingPlugin
~~~~~~~~~~

**Command:** ``ping``, ``p``, or ``p`` followed by a space

**Description:** Responds with "Pong!" and the current time.

**Usage:** Send a message containing "ping" to your APRSD callsign.

**Example:**
   ::

      You: ping
      APRSD: Pong! 14:30:05

**Configuration:** No configuration required.

**Plugin Path:** ``aprsd.plugins.ping.PingPlugin``


FortunePlugin
~~~~~~~~~~~~~

**Command:** ``fortune``, ``f``, or ``f`` followed by a space

**Description:** Returns a random fortune cookie message using the system's ``fortune`` command.

**Usage:** Send a message containing "fortune" to your APRSD callsign.

**Requirements:** Requires the ``fortune`` command to be installed on the system. The plugin
will automatically search common installation paths and disable itself if not found.

**Example:**
   ::

      You: fortune
      APRSD: A journey of a thousand miles begins with a single step.

**Configuration:** No configuration required.

**Plugin Path:** ``aprsd.plugins.fortune.FortunePlugin``


TimePlugin
~~~~~~~~~~

**Command:** ``time``, ``t``, or ``t`` followed by a space

**Description:** Returns the current local time of the APRSD server in a human-readable format
(fuzzy time) with timezone information.

**Usage:** Send a message containing "time" to your APRSD callsign.

**Example:**
   ::

      You: time
      APRSD: half past two (14:30 PDT)

**Configuration:** No configuration required. Uses the system's local timezone.

**Plugin Path:** ``aprsd.plugins.time.TimePlugin``


VersionPlugin
~~~~~~~~~~~~~

**Command:** ``version``, ``v``, or ``v`` followed by a space

**Description:** Returns the APRSD version number and server uptime.

**Usage:** Send a message containing "version" to your APRSD callsign.

**Example:**
   ::

      You: version
      APRSD: APRSD ver:4.2.4 uptime:2 days, 5:30:15

**Configuration:** No configuration required.

**Plugin Path:** ``aprsd.plugins.version.VersionPlugin``


USWeatherPlugin
~~~~~~~~~~~~~~~

**Command:** ``weather``, ``w``, or ``W`` (w or W at start of message)

**Description:** Provides weather information for locations within the United States only.
Uses the forecast.weather.gov API to fetch weather data based on the GPS beacon location
of the calling callsign (or optionally a specified callsign).

**Usage:**
   ::

      You: weather
      APRSD: 72F(68F/75F) Partly cloudy. Tonight, Clear.

      You: weather WB4BOR
      APRSD: 65F(60F/70F) Sunny. Tonight, Partly cloudy.

**Requirements:** Requires an ``aprs_fi.apiKey`` configuration option.

**Configuration:**
   - ``aprs_fi.apiKey`` - API key from aprs.fi account

**Note:** This plugin does not require an API key for the weather service itself, only
for aprs.fi to get the GPS location.

**Plugin Path:** ``aprsd.plugins.weather.USWeatherPlugin``


USMetarPlugin
~~~~~~~~~~~~~

**Command:** ``metar``, ``m``, ``M``, or ``m`` followed by a space (m or M at start of message)

**Description:** Provides METAR (Meteorological Aerodrome Report) weather reports for
stations within the United States only. Uses the forecast.weather.gov API.

**Usage:**
   ::

      You: metar
      APRSD: KORD 101451Z 28010KT 10SM FEW250 22/12 A3001

      You: metar KORD
      APRSD: KORD 101451Z 28010KT 10SM FEW250 22/12 A3001

**Requirements:** Requires an ``aprs_fi.apiKey`` configuration option (when querying
by callsign location).

**Configuration:**
   - ``aprs_fi.apiKey`` - API key from aprs.fi account

**Note:** When specifying a station identifier directly (e.g., "metar KORD"), the
aprs.fi API key is not required.

**Plugin Path:** ``aprsd.plugins.weather.USMetarPlugin``


HelpPlugin
~~~~~~~~~~

**Command:** ``help``, ``h``, or ``H`` (h or H at start of message)

**Description:** Provides help information about available plugins. Can list all available
plugins or provide specific help for a named plugin.

**Usage:**
   ::

      You: help
      APRSD: Send APRS MSG of 'help' or 'help <plugin>'
             plugins: fortune ping time version weather

      You: help weather
      APRSD: openweathermap: Send ^[wW] to get weather from your location
             openweathermap: Send ^[wW] <callsign> to get weather from <callsign>

**Configuration:** Can be disabled by setting ``load_help_plugin = false`` in the configuration.

**Plugin Path:** ``aprsd.plugin.HelpPlugin``


WatchList Plugins
-----------------

These plugins monitor APRS traffic and can send notifications based on watch list criteria.

NotifySeenPlugin
~~~~~~~~~~~~~~~~

**Type:** WatchList Plugin

**Description:** Monitors callsigns in the watch list and sends a notification message when
a callsign that hasn't been seen recently (based on the configured age limit) appears on
the APRS network.

**How it works:**
   - Tracks callsigns configured in the watch list
   - Monitors all incoming APRS packets
   - When a callsign in the watch list is seen and hasn't been seen recently (exceeds
     the age limit), sends a notification message to the configured alert callsign

**Configuration:**
   - ``watch_list.enabled`` - Must be set to ``true``
   - ``watch_list.callsigns`` - List of callsigns to watch for
   - ``watch_list.alert_callsign`` - Callsign to send notifications to
   - ``watch_list.alert_time_seconds`` - Time threshold in seconds (default: 3600)

**Example Notification:**
   ::

      APRSD -> WB4BOR: KM6LYW was just seen by type:'BeaconPacket'

**Plugin Path:** ``aprsd.plugins.notify.NotifySeenPlugin``


Enabling Built-in Plugins
--------------------------

Built-in plugins are enabled through the ``enabled_plugins`` configuration option in your
APRSD configuration file. List the full Python path to each plugin class you want to enable.

**Example Configuration:**
   ::

      [DEFAULT]
      enabled_plugins = aprsd.plugins.fortune.FortunePlugin,aprsd.plugins.ping.PingPlugin,aprsd.plugins.time.TimePlugin,aprsd.plugins.weather.USWeatherPlugin,aprsd.plugins.version.VersionPlugin,aprsd.plugins.notify.NotifySeenPlugin

**Note:** The HelpPlugin is enabled by default and does not need to be listed in
``enabled_plugins``. It can be disabled by setting ``load_help_plugin = false``.

**Note:** Some plugins may require additional configuration (API keys, etc.) and will
automatically disable themselves if required configuration is missing.

**Note:** Weather plugins may use the same command patterns. Only one weather plugin should
be enabled at a time to avoid conflicts. Similarly, only one METAR plugin should be enabled
at a time.


Listing Available Plugins
--------------------------

You can see all available built-in plugins, along with their descriptions and command patterns,
by running:

.. code-block:: shell

   aprsd list-plugins

This command will show:
   - Built-in plugins included with APRSD
   - Available plugins on PyPI that can be installed
   - Currently installed third-party plugins


Finding External Plugins and Extensions
=========================================

APRSD supports external plugins and extensions that extend the functionality beyond the
built-in plugins. These are distributed as separate Python packages that follow a specific
naming convention.

Naming Convention
-----------------

All external APRSD plugins and extensions follow a consistent naming scheme:

* **Plugins:** ``aprsd-<name>-plugin``
* **Extensions:** ``aprsd-<name>-extension``

For example:
* ``aprsd-email-plugin`` - A plugin for email functionality
* ``aprsd-admin-extension`` - An extension for web administration

Finding Plugins and Extensions
-------------------------------

PyPI (Python Package Index)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can find all available APRSD plugins and extensions on PyPI:

* **Search for plugins:** https://pypi.org/search/?q=aprsd+-plugin
* **Search for extensions:** https://pypi.org/search/?q=aprsd+-extension
* **General APRSD search:** https://pypi.org/search/?q=aprsd

The ``aprsd list-plugins`` command also shows available plugins and extensions from PyPI
along with installation status.

GitHub
~~~~~~

Many APRSD plugins and extensions are hosted on GitHub under the `hemna organization`_:

* **Organization:** https://github.com/hemna/
* **Search for plugins:** https://github.com/orgs/hemna/repositories?q=aprsd-plugin
* **Search for extensions:** https://github.com/orgs/hemna/repositories?q=aprsd-extension

Installing External Plugins and Extensions
-------------------------------------------

To install an external plugin or extension, use pip:

.. code-block:: shell

   pip install aprsd-<name>-plugin
   # or
   pip install aprsd-<name>-extension

After installation, the plugin or extension will be automatically discovered by APRSD.
You may need to add it to your ``enabled_plugins`` configuration or configure it according
to its documentation.

Available External Plugins
---------------------------

The following external plugins are available:

Email Plugin
~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-email-plugin/
* **GitHub:** https://github.com/hemna/aprsd-email-plugin
* **Description:** Send and receive email via APRS messages.

Location Plugin
~~~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-location-plugin/
* **GitHub:** https://github.com/hemna/aprsd-location-plugin
* **Description:** Get the latest GPS location of a callsign.

Location Data Plugin
~~~~~~~~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-locationdata-plugin/
* **GitHub:** https://github.com/hemna/aprsd-locationdata-plugin
* **Description:** Get detailed GPS location data for a callsign.

DigiPi Plugin
~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-digipi-plugin/
* **GitHub:** https://github.com/hemna/aprsd-digipi-plugin
* **Description:** Look for DigiPi beacon packets and provide DigiPi-specific functionality.

W3W Plugin
~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-w3w-plugin/
* **GitHub:** https://github.com/hemna/aprsd-w3w-plugin
* **Description:** Get What3Words (w3w) coordinates for a location.

MQTT Plugin
~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-mqtt-plugin/
* **GitHub:** https://github.com/hemna/aprsd-mqtt-plugin
* **Description:** Send APRS packets to an MQTT topic for integration with IoT systems.

Telegram Plugin
~~~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-telegram-plugin/
* **GitHub:** https://github.com/hemna/aprsd-telegram-plugin
* **Description:** Send and receive messages via Telegram.

Borat Plugin
~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-borat-plugin/
* **GitHub:** https://github.com/hemna/aprsd-borat-plugin
* **Description:** Get random Borat quotes via APRS messages.

WXNow Plugin
~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-wxnow-plugin/
* **GitHub:** https://github.com/hemna/aprsd-wxnow-plugin
* **Description:** Get weather reports from the closest N weather stations.

WeeWX Plugin
~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-weewx-plugin/
* **GitHub:** https://github.com/hemna/aprsd-weewx-plugin
* **Description:** Get weather data from your WeeWX weather station.

Slack Plugin
~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-slack-plugin/
* **GitHub:** https://github.com/hemna/aprsd-slack-plugin
* **Description:** Send and receive messages to/from a Slack channel.

Sentry Plugin
~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-sentry-plugin/
* **GitHub:** https://github.com/hemna/aprsd-sentry-plugin
* **Description:** Integration with Sentry for error tracking and monitoring.

Repeat Plugins
~~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-repeat-plugins/
* **GitHub:** https://github.com/hemna/aprsd-repeat-plugins
* **Description:** Plugins for the REPEAT service - get nearest Ham radio repeaters.

Twitter Plugin
~~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-twitter-plugin/
* **GitHub:** https://github.com/hemna/aprsd-twitter-plugin
* **Description:** Make tweets from your Ham Radio via APRS messages.

Time OpenCage Plugin
~~~~~~~~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-timeopencage-plugin/
* **GitHub:** https://github.com/hemna/aprsd-timeopencage-plugin
* **Description:** Get local time for a callsign using OpenCage geocoding.

Stock Plugin
~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-stock-plugin/
* **GitHub:** https://github.com/hemna/aprsd-stock-plugin
* **Description:** Get stock quotes from your Ham radio via APRS messages.

Available External Extensions
-----------------------------

The following external extensions are available:

Admin Extension
~~~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-admin-extension/
* **GitHub:** https://github.com/hemna/aprsd-admin-extension
* **Description:** Web-based administration interface for APRSD with real-time status,
  configuration management, and monitoring capabilities.

WebChat Extension
~~~~~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-webchat-extension/
* **GitHub:** https://github.com/hemna/aprsd-webchat-extension
* **Description:** Web-based APRS messaging interface that allows you to send and receive
  APRS messages through a browser.

Rich CLI Extension
~~~~~~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-rich-cli-extension/
* **GitHub:** https://github.com/hemna/aprsd-rich-cli-extension
* **Description:** Enhanced Textual-based rich CLI versions of APRSD commands with improved
  user interface and interactivity.

IRC Extension
~~~~~~~~~~~~~

* **PyPI:** https://pypi.org/project/aprsd-irc-extension/
* **GitHub:** https://github.com/hemna/aprsd-irc-extension
* **Description:** IRC-like server command for APRS, providing an IRC-style interface to
  the APRS network.

.. _hemna organization: https://github.com/hemna

.. include:: links.rst
