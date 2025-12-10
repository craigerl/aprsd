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

**Command:** ``ping``, ``p``, or ``p `` (p followed by space)

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

**Command:** ``fortune``, ``f``, or ``f `` (f followed by space)

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

**Command:** ``time``, ``t``, or ``t `` (t followed by space)

**Description:** Returns the current local time of the APRSD server in a human-readable format
with timezone information.

**Usage:** Send a message containing "time" to your APRSD callsign.

**Example:**
   ::

      You: time
      APRSD: half past two (14:30 PDT)

**Configuration:** No configuration required. Uses the system's local timezone.

**Plugin Path:** ``aprsd.plugins.time.TimePlugin``


TimeOWMPlugin
~~~~~~~~~~~~~

**Command:** ``time``, ``t``, or ``t `` (t followed by space)

**Description:** Returns the current time based on the GPS beacon location of the calling
callsign (or optionally a specified callsign). Uses OpenWeatherMap API to determine the
timezone for the location.

**Usage:**
   ::

      You: time
      APRSD: quarter to three (14:45 EST)

      You: time WB4BOR
      APRSD: half past two (14:30 PDT)

**Requirements:**
   - Requires an ``aprs_fi.apiKey`` configuration option
   - Requires an ``owm_weather_plugin.apiKey`` configuration option

**Configuration:**
   - ``aprs_fi.apiKey`` - API key from aprs.fi account
   - ``owm_weather_plugin.apiKey`` - OpenWeatherMap API key

**Plugin Path:** ``aprsd.plugins.time.TimeOWMPlugin``


VersionPlugin
~~~~~~~~~~~~~

**Command:** ``version``, ``v``, or ``v `` (v followed by space)

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

**Command:** ``metar``, ``m``, ``M``, or ``m `` (m or M at start of message)

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


OWMWeatherPlugin
~~~~~~~~~~~~~~~~

**Command:** ``weather``, ``w``, or ``W`` (w or W at start of message)

**Description:** Provides weather information using the OpenWeatherMap API. Works worldwide
and provides current weather conditions including temperature, dew point, wind speed and
direction, and humidity.

**Usage:**
   ::

      You: weather
      APRSD: clear sky 72.1F/65.2F Wind 5@270 45%

      You: weather WB4BOR
      APRSD: partly cloudy 68.5F/62.1F Wind 8@180G12 52%

**Requirements:**
   - Requires an ``aprs_fi.apiKey`` configuration option
   - Requires an ``owm_weather_plugin.apiKey`` configuration option

**Configuration:**
   - ``aprs_fi.apiKey`` - API key from aprs.fi account
   - ``owm_weather_plugin.apiKey`` - OpenWeatherMap API key (get one at https://home.openweathermap.org/api_keys)
   - ``units`` - Set to "imperial" or "metric" (default: "imperial")

**Plugin Path:** ``aprsd.plugins.weather.OWMWeatherPlugin``


AVWXWeatherPlugin
~~~~~~~~~~~~~~~~~

**Command:** ``metar``, ``m``, ``m `` (m at start of message)

**Description:** Provides METAR weather reports using the AVWX API service. Fetches METAR
data from the nearest weather station to the GPS beacon location of the calling callsign
(or optionally a specified callsign).

**Usage:**
   ::

      You: metar
      APRSD: KORD 101451Z 28010KT 10SM FEW250 22/12 A3001 RMK AO2 SLP168 T02220122

      You: metar WB4BOR
      APRSD: KSFO 101500Z 25015KT 10SM FEW030 18/14 A2998 RMK AO2

**Requirements:**
   - Requires an ``aprs_fi.apiKey`` configuration option
   - Requires an ``avwx_plugin.apiKey`` configuration option
   - Requires an ``avwx_plugin.base_url`` configuration option

**Configuration:**
   - ``aprs_fi.apiKey`` - API key from aprs.fi account
   - ``avwx_plugin.apiKey`` - API key for AVWX service
   - ``avwx_plugin.base_url`` - Base URL for AVWX API (default: https://avwx.rest)

**Note:** AVWX is an open-source project. You can use the hosted service at https://avwx.rest/
or host your own instance. See the plugin code comments for instructions on running your
own AVWX API server.

**Plugin Path:** ``aprsd.plugins.weather.AVWXWeatherPlugin``


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
      enabled_plugins = aprsd.plugins.fortune.FortunePlugin,aprsd.plugins.ping.PingPlugin,aprsd.plugins.time.TimePlugin,aprsd.plugins.weather.OWMWeatherPlugin,aprsd.plugins.version.VersionPlugin,aprsd.plugins.notify.NotifySeenPlugin

**Note:** The HelpPlugin is enabled by default and does not need to be listed in
``enabled_plugins``. It can be disabled by setting ``load_help_plugin = false``.

**Note:** Some plugins may require additional configuration (API keys, etc.) and will
automatically disable themselves if required configuration is missing.

**Note:** Weather plugins (USWeatherPlugin, OWMWeatherPlugin, AVWXWeatherPlugin) all use
the same command pattern (``w`` or ``W`` at the start). Only one should be enabled at a time
to avoid conflicts. Similarly, METAR plugins (USMetarPlugin, AVWXWeatherPlugin) use the
same pattern (``m`` or ``M`` at the start).


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

.. include:: links.rst
