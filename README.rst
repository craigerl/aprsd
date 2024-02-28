===============================================
APRSD - Ham radio APRS-IS Message plugin server
===============================================

KM6LYW and WB4BOR
____________________

|pypi| |pytest| |versions| |slack| |issues| |commit| |imports| |down|


`APRSD <http://github.com/craigerl/aprsd>`_ is a Ham radio `APRS <http://aprs.org>`_ message command gateway built on python.


What is APRSD
=============
APRSD is a python application for interacting with the APRS network and providing
APRS services for HAM radio operators.

APRSD currently has 4 main commands to use.
    * server - Connect to APRS and listen/respond to APRS messages
    * webchat - web based chat program over APRS
    * send-message - Send a message to a callsign via APRS_IS.
    * listen - Listen to packets on the APRS-IS Network based on FILTER.

Each of those commands can connect to the APRS-IS network if internet connectivity
is available.  If internet is not available, then APRS can be configured to talk
to a TCP KISS TNC for radio connectivity.

Please `read the docs`_ to learn more!

APRSD Overview Diagram
======================

.. image:: https://raw.githubusercontent.com/craigerl/aprsd/master/docs/_static/aprsd_overview.svg?sanitize=true

Typical use case
================

APRSD's typical use case is that of providing an APRS wide service to all HAM
radio operators.  For example the callsign 'REPEAT' on the APRS network is actually
an instance of APRSD that can provide a list of HAM repeaters in the area of the
callsign that sent the message.


Ham radio operator using an APRS enabled HAM radio sends a message to check
the weather.  An APRS message is sent, and then picked up by APRSD.  The
APRS packet is decoded, and the message is sent through the list of plugins
for processing.  For example, the WeatherPlugin picks up the message, fetches the weather
for the area around the user who sent the request, and then responds with
the weather conditions in that area.  Also includes a watch list of HAM
callsigns to look out for.  The watch list can notify you when a HAM callsign
in the list is seen and now available to message on the APRS network.



Installation
=============

To install ``aprsd``, use Pip:

``pip install aprsd``

Example usage
==============

``aprsd -h``

Help
====
::

    └─> aprsd -h
    Usage: aprsd [OPTIONS] COMMAND [ARGS]...

    Options:
      --version   Show the version and exit.
      -h, --help  Show this message and exit.

    Commands:
      check-version  Check this version against the latest in pypi.org.
      completion     Click Completion subcommands
      dev            Development type subcommands
      healthcheck    Check the health of the running aprsd server.
      list-plugins   List the built in plugins available to APRSD.
      listen         Listen to packets on the APRS-IS Network based on FILTER.
      sample-config  Generate a sample Config file from aprsd and all...
      send-message   Send a message to a callsign via APRS_IS.
      server         Start the aprsd server gateway process.
      version        Show the APRSD version.
      webchat        Web based HAM Radio chat program!



Commands
========

Configuration
=============
This command outputs a sample config yml formatted block that you can edit
and use to pass in to ``aprsd`` with ``-c``.  By default aprsd looks in ``~/.config/aprsd/aprsd.yml``

``aprsd sample-config``

::

    └─> aprsd sample-config
    ...

server
======

This is the main server command that will listen to APRS-IS servers and
look for incomming commands to the callsign configured in the config file

::

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
    Load config
    12/07/2021 03:16:17 PM MainThread      INFO     APRSD is up to date                                                                   server.py:51
    12/07/2021 03:16:17 PM MainThread      INFO     APRSD Started version: 2.5.6                                                          server.py:52
    12/07/2021 03:16:17 PM MainThread      INFO     Using CONFIG values:                                                                  server.py:55
    12/07/2021 03:16:17 PM MainThread      INFO     ham.callsign = WB4BOR                                                                 server.py:60
    12/07/2021 03:16:17 PM MainThread      INFO     aprs.login = WB4BOR-12                                                                server.py:60
    12/07/2021 03:16:17 PM MainThread      INFO     aprs.password = XXXXXXXXXXXXXXXXXXX                                                   server.py:58
    12/07/2021 03:16:17 PM MainThread      INFO     aprs.host = noam.aprs2.net                                                            server.py:60
    12/07/2021 03:16:17 PM MainThread      INFO     aprs.port = 14580                                                                     server.py:60
    12/07/2021 03:16:17 PM MainThread      INFO     aprs.logfile = /tmp/aprsd.log                                                         server.py:60


Current list of built-in plugins
======================================

::

    └─> aprsd list-plugins
                                                           🐍 APRSD Built-in Plugins 🐍
    ┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃ Plugin Name       ┃ Info                                                       ┃ Type         ┃ Plugin Path                             ┃
    ┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
    │ AVWXWeatherPlugin │ AVWX weather of GPS Beacon location                        │ RegexCommand │ aprsd.plugins.weather.AVWXWeatherPlugin │
    │ EmailPlugin       │ Send and Receive email                                     │ RegexCommand │ aprsd.plugins.email.EmailPlugin         │
    │ FortunePlugin     │ Give me a fortune                                          │ RegexCommand │ aprsd.plugins.fortune.FortunePlugin     │
    │ LocationPlugin    │ Where in the world is a CALLSIGN's last GPS beacon?        │ RegexCommand │ aprsd.plugins.location.LocationPlugin   │
    │ NotifySeenPlugin  │ Notify me when a CALLSIGN is recently seen on APRS-IS      │ WatchList    │ aprsd.plugins.notify.NotifySeenPlugin   │
    │ OWMWeatherPlugin  │ OpenWeatherMap weather of GPS Beacon location              │ RegexCommand │ aprsd.plugins.weather.OWMWeatherPlugin  │
    │ PingPlugin        │ reply with a Pong!                                         │ RegexCommand │ aprsd.plugins.ping.PingPlugin           │
    │ QueryPlugin       │ APRSD Owner command to query messages in the MsgTrack      │ RegexCommand │ aprsd.plugins.query.QueryPlugin         │
    │ TimeOWMPlugin     │ Current time of GPS beacon's timezone. Uses OpenWeatherMap │ RegexCommand │ aprsd.plugins.time.TimeOWMPlugin        │
    │ TimePlugin        │ What is the current local time.                            │ RegexCommand │ aprsd.plugins.time.TimePlugin           │
    │ USMetarPlugin     │ USA only METAR of GPS Beacon location                      │ RegexCommand │ aprsd.plugins.weather.USMetarPlugin     │
    │ USWeatherPlugin   │ Provide USA only weather of GPS Beacon location            │ RegexCommand │ aprsd.plugins.weather.USWeatherPlugin   │
    │ VersionPlugin     │ What is the APRSD Version                                  │ RegexCommand │ aprsd.plugins.version.VersionPlugin     │
    └───────────────────┴────────────────────────────────────────────────────────────┴──────────────┴─────────────────────────────────────────┘


                                                    Pypi.org APRSD Installable Plugin Packages

                                   Install any of the following plugins with 'pip install <Plugin Package Name>'
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
    ┃ Plugin Package Name          ┃ Description                                                        ┃ Version ┃   Released   ┃ Installed? ┃
    ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
    │ 📂 aprsd-stock-plugin        │ Ham Radio APRSD Plugin for fetching stock quotes                   │  0.1.3  │ Dec 2, 2022  │     No     │
    │ 📂 aprsd-sentry-plugin       │ Ham radio APRSD plugin that does....                               │  0.1.2  │ Dec 2, 2022  │     No     │
    │ 📂 aprsd-timeopencage-plugin │ APRSD plugin for fetching time based on GPS location               │  0.1.0  │ Dec 2, 2022  │     No     │
    │ 📂 aprsd-weewx-plugin        │ HAM Radio APRSD that reports weather from a weewx weather station. │  0.1.4  │ Dec 7, 2021  │    Yes     │
    │ 📂 aprsd-repeat-plugins      │ APRSD Plugins for the REPEAT service                               │ 1.0.12  │ Dec 2, 2022  │     No     │
    │ 📂 aprsd-telegram-plugin     │ Ham Radio APRS APRSD plugin for Telegram IM service                │  0.1.3  │ Dec 2, 2022  │     No     │
    │ 📂 aprsd-twitter-plugin      │ Python APRSD plugin to send tweets                                 │  0.3.0  │ Dec 7, 2021  │     No     │
    │ 📂 aprsd-slack-plugin        │ Amateur radio APRS daemon which listens for messages and responds  │  1.0.5  │ Dec 18, 2022 │     No     │
    └──────────────────────────────┴────────────────────────────────────────────────────────────────────┴─────────┴──────────────┴────────────┘


                                      🐍 APRSD Installed 3rd party Plugins 🐍
    ┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃ Package Name       ┃ Plugin Name     ┃ Version ┃ Type         ┃ Plugin Path                              ┃
    ┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
    │ aprsd-weewx-plugin │ WeewxMQTTPlugin │   1.0   │ RegexCommand │ aprsd_weewx_plugin.weewx.WeewxMQTTPlugin │
    └────────────────────┴─────────────────┴─────────┴──────────────┴──────────────────────────────────────────┘



send-message
============

This command is typically used for development to send another aprsd instance
test messages

::

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


SEND EMAIL (radio to smtp server)
=================================

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
====================================

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


LOCATION
========

::

    Received Message _______________
    Raw         : KM6XXX-6>APRS,TCPIP*,qAC,T2CAEAST::KM6XXX-14:location{2
    From        : KM6XXX-6
    Message     : location
    Msg number  : 2
    Received Message _______________ Complete

    Sending Message _______________
    Raw         : KM6XXX-14>APRS::KM6XXX-6 :KM6XXX-6: 8 Miles E Auburn CA 0' 0,-120.93584 1873.7h ago{2
    To          : KM6XXX-6
    Message     : KM6XXX-6: 8 Miles E Auburn CA 0' 0,-120.93584 1873.7h ago
    Msg number  : 2
    Sending Message _______________ Complete

    Sending ack _______________
    Raw         : KM6XXX-14>APRS::KM6XXX-6 :ack2
    To          : KM6XXX-6
    Ack         : 2
    Sending ack _______________ Complete

AND... ping, fortune, time.....


Web Admin Interface
===================
To start the web admin interface, You have to install gunicorn in your virtualenv that already has aprsd installed.

::

  source <path to APRSD's virtualenv>/bin/activate
  pip install gunicorn
  gunicorn --bind 0.0.0.0:8080 "aprsd.wsgi:app"

The web admin interface will be running on port 8080 on the local machine.  http://localhost:8080



Development
===========

* ``git clone git@github.com:craigerl/aprsd.git``
* ``cd aprsd``
* ``make``

Workflow
========

While working aprsd, The workflow is as follows:

* Checkout a new branch to work on by running

  ``git checkout -b mybranch``

* Make your changes to the code
* Run Tox with the following options:

  - ``tox -epep8``
  - ``tox -efmt``
  - ``tox -p``

* Commit your changes. This will run the pre-commit hooks which does checks too

  ``git commit``

* Once you are done with all of your commits, then push up the branch to
  github with:

  ``git push -u origin mybranch``

* Create a pull request from your branch so github tests can run and we can do
  a code review.


Release
=======

To do release to pypi:

* Tag release with:

  ``git tag -v1.XX -m "New release"``

* Push release tag:

  ``git push origin master --tags``

* Do a test build and verify build is valid by running:

  ``make build``

* Once twine is happy, upload release to pypi:

  ``make upload``


Docker Container
================

Building
========

There are 2 versions of the container Dockerfile that can be used.
The main Dockerfile, which is for building the official release container
based off of the pip install version of aprsd and the Dockerfile-dev,
which is used for building a container based off of a git branch of
the repo.

Official Build
==============

``docker build -t hemna6969/aprsd:latest .``

Development Build
=================

``docker build -t hemna6969/aprsd:latest -f Dockerfile-dev .``


Running the container
=====================

There is a ``docker-compose.yml`` file in the ``docker/`` directory
that can be used to run your container. To provide the container
an ``aprsd.conf`` configuration file, change your
``docker-compose.yml`` as shown below:

::

     volumes:
         - $HOME/.config/aprsd:/config

To install plugins at container start time, pass in a list of
comma-separated list of plugins on PyPI using the ``APRSD_PLUGINS``
environment variable in the ``docker-compose.yml`` file. Note that
version constraints may also be provided. For example:

::

    environment:
        - APRSD_PLUGINS=aprsd-slack-plugin>=1.0.2,aprsd-twitter-plugin


.. badges

.. |pypi| image:: https://badge.fury.io/py/aprsd.svg
    :target: https://badge.fury.io/py/aprsd

.. |pytest| image:: https://github.com/craigerl/aprsd/workflows/python/badge.svg
    :target: https://github.com/craigerl/aprsd/actions

.. |versions| image:: https://img.shields.io/pypi/pyversions/aprsd.svg
    :target: https://pypi.org/pypi/aprsd

.. |slack| image:: https://img.shields.io/badge/slack-@hemna/aprsd-blue.svg?logo=slack
    :target: https://hemna.slack.com/app_redirect?channel=C01KQSCP5RP

.. |imports| image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
    :target: https://timothycrosley.github.io/isort/

.. |issues| image:: https://img.shields.io/github/issues/craigerl/aprsd

.. |commit| image:: https://img.shields.io/github/last-commit/craigerl/aprsd

.. |down| image:: https://static.pepy.tech/personalized-badge/aprsd?period=month&units=international_system&left_color=black&right_color=orange&left_text=Downloads
     :target: https://pepy.tech/project/aprsd

.. links
.. _read the docs:
 https://aprsd.readthedocs.io
