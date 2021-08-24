===============================================
APRSD - Ham radio APRS-IS Message plugin server
===============================================

KM6LYW and WB4BOR
____________________

|pypi| |pytest| |versions| |slack| |issues| |commit| |imports| |down|


`APRSD <http://github.com/craigerl/aprsd>`_ is a Ham radio `APRS <http://aprs.org>`_ message command gateway built on python.

APRSD listens on amateur radio aprs-is network for messages and respond to them.
It has a plugin architecture for extensibility.  Users of APRSD can write their own
plugins that can respond to APRS-IS messages.

You must have an amateur radio callsign to use this software.  APRSD gets
messages for the configured HAM callsign, and sends those messages to a
list of plugins for processing.   There are a set of core plugins that
provide responding to messages to check email, get location, ping,
time of day, get weather, and fortune telling as well as version information
of aprsd itself.

Please `read the docs`_ to learn more!


.. contents:: :local:


APRSD Overview Diagram
----------------------

.. image:: https://raw.githubusercontent.com/craigerl/aprsd/master/docs/_static/aprsd_overview.svg?sanitize=true


Typical use case
================

Ham radio operator using an APRS enabled HAM radio sends a message to check
the weather.  An APRS message is sent, and then picked up by APRSD.  The
APRS packet is decoded, and the message is sent through the list of plugins
for processing.  For example, the WeatherPlugin picks up the message, fetches the weather
for the area around the user who sent the request, and then responds with
the weather conditions in that area.  Also includes a watch list of HAM
callsigns to look out for.  The watch list can notify you when a HAM callsign
in the list is seen and now available to message on the APRS network.


List of core server plugins
===========================

Plugins function by specifying a regex that is searched for in the APRS message.
If it matches, the plugin runs.  IF the regex doesn't match, the plugin is skipped.

* EmailPlugin - Check email and reply with contents.  Have to configure IMAP and SMTP settings in aprs.yml
* FortunePlugin - Replies with old unix fortune random fortune!
* LocationPlugin - Checks location of ham operator
* PingPlugin - Sends pong with timestamp
* QueryPlugin - Allows querying the list of delayed messages that were not ACK'd by radio
* TimePlugin - Current time of day
* WeatherPlugin - Get weather conditions for current location of HAM callsign
* VersionPlugin - Reports the version information for aprsd
* NotifySeenPlugin - Send a message when a message is seen from a callsign in
                     the watch list.  This is helpful when you want to know
                     when a friend is online in the ARPS network, but haven't
                     been seen in a while.


Current messages this will respond to:
======================================

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
   v(ersion)              = Respond with current APRSD Version string
   anything else          = respond with usage


Meanwhile this code will monitor a single imap mailbox and forward email
to your BASECALLSIGN over the air.  Only radios using the BASECALLSIGN are allowed
to send email, so consider this security risk before using this (or Amatuer radio in
general).  Email is single user at this time.

There are additional parameters in the code (sorry), so be sure to set your
email server, and associated logins, passwords.  search for "yourdomain",
"password".  Search for "shortcuts" to setup email aliases as well.


Installation:
=============

  pip install aprsd

Example usage:
==============

  aprsd -h

Help
====
::

    └─[$] > aprsd -h
    Usage: aprsd [OPTIONS] COMMAND [ARGS]...

      Shell completion for click-completion-command Available shell types:
      bash         Bourne again shell   fish         Friendly interactive shell
      powershell   Windows PowerShell   zsh          Z shell Default type: auto

    Options:
      --version   Show the version and exit.
      -h, --help  Show this message and exit.

    Commands:
      install        Install the click-completion-command completion
      sample-config  This dumps the config to stdout.
      send-message   Send a message to a callsign via APRS_IS.
      server         Start the aprsd server process.
      show           Show the click-completion-command completion code



Commands
========

Configuration
=============
This command outputs a sample config yml formatted block that you can edit
and use to pass in to aprsd with -c.  By default aprsd looks in ~/.config/aprsd/aprsd.yml

  aprsd sample-config

Output
======
::

    └─> aprsd sample-config
    aprs:
        # Get the passcode for your callsign here:
        # https://apps.magicbug.co.uk/passcode
        host: rotate.aprs2.net
        login: CALLSIGN
        password: '00000'
        port: 14580
    aprsd:
        dateformat: '%m/%d/%Y %I:%M:%S %p'
        email:
            enabled: true
            imap:
                debug: false
                host: imap.gmail.com
                login: IMAP_USERNAME
                password: IMAP_PASSWORD
                port: 993
                use_ssl: true
            shortcuts:
                aa: 5551239999@vtext.com
                cl: craiglamparter@somedomain.org
                wb: 555309@vtext.com
            smtp:
                debug: false
                host: smtp.gmail.com
                login: SMTP_USERNAME
                password: SMTP_PASSWORD
                port: 465
                use_ssl: false
        enabled_plugins:
        - aprsd.plugins.email.EmailPlugin
        - aprsd.plugins.fortune.FortunePlugin
        - aprsd.plugins.location.LocationPlugin
        - aprsd.plugins.ping.PingPlugin
        - aprsd.plugins.query.QueryPlugin
        - aprsd.plugins.stock.StockPlugin
        - aprsd.plugins.time.TimePlugin
        - aprsd.plugins.weather.USWeatherPlugin
        - aprsd.plugins.version.VersionPlugin
        logfile: /tmp/aprsd.log
        logformat: '[%(asctime)s] [%(threadName)-12s] [%(levelname)-5.5s] %(message)s - [%(pathname)s:%(lineno)d]'
        trace: false
        units: imperial
        web:
            enabled: true
            host: 0.0.0.0
            logging_enabled: true
            port: 8001
            users:
                admin: aprsd
    ham:
        callsign: CALLSIGN
    services:
        aprs.fi:
            # Get the apiKey from your aprs.fi account here:
            # http://aprs.fi/account
            apiKey: APIKEYVALUE
        avwx:
            # (Optional for AVWXWeatherPlugin)
            # Use hosted avwx-api here: https://avwx.rest
            # or deploy your own from here:
            # https://github.com/avwx-rest/avwx-api
            apiKey: APIKEYVALUE
            base_url: http://host:port
        opencagedata:
            # (Optional for TimeOpenCageDataPlugin)
            # Get the apiKey from your opencagedata account here:
            # https://opencagedata.com/dashboard#api-keys
            apiKey: APIKEYVALUE
        openweathermap:
            # (Optional for OWMWeatherPlugin)
            # Get the apiKey from your
            # openweathermap account here:
            # https://home.openweathermap.org/api_keys
            apiKey: APIKEYVALUE

server
======

This is the main server command that will listen to APRS-IS servers and
look for incomming commands to the callsign configured in the config file

::

    └─[$] > aprsd server --help
    Usage: aprsd server [OPTIONS]

      Start the aprsd server process.

    Options:
      --loglevel [CRITICAL|ERROR|WARNING|INFO|DEBUG]
                                      The log level to use for aprsd.log
                                      [default: INFO]

      --quiet                         Don't log to stdout
      --disable-validation            Disable email shortcut validation.  Bad
                                      email addresses can result in broken email
                                      responses!!

      -c, --config TEXT               The aprsd config file to use for options.
                                      [default:
                                      /home/waboring/.config/aprsd/aprsd.yml]

      -f, --flush                     Flush out all old aged messages on disk.
                                      [default: False]

      -h, --help                      Show this message and exit.

      $ aprsd server
    Load config
    [02/13/2021 09:22:09 AM] [MainThread  ] [INFO ] APRSD Started version: 1.6.0
    [02/13/2021 09:22:09 AM] [MainThread  ] [INFO ] Checking IMAP configuration
    [02/13/2021 09:22:09 AM] [MainThread  ] [INFO ] Checking SMTP configuration
    [02/13/2021 09:22:10 AM] [MainThread  ] [INFO ] Validating 2 Email shortcuts. This can take up to 10 seconds per shortcut


send-message
============

This command is typically used for development to send another aprsd instance
test messages

::

    └─[$] > aprsd send-message -h
    Usage: aprsd send-message [OPTIONS] TOCALLSIGN [COMMAND]...

      Send a message to a callsign via APRS_IS.

    Options:
      --loglevel [CRITICAL|ERROR|WARNING|INFO|DEBUG]
                                      The log level to use for aprsd.log
                                      [default: DEBUG]

      --quiet                         Don't log to stdout
      -c, --config TEXT               The aprsd config file to use for options.
                                      [default: ~/.config/aprsd/aprsd.yml]

      --aprs-login TEXT               What callsign to send the message from.
                                      [env var: APRS_LOGIN]

      --aprs-password TEXT            the APRS-IS password for APRS_LOGIN  [env
                                      var: APRS_PASSWORD]

      -h, --help                      Show this message and exit.


Example output:
===============


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


Development
===========

* git clone git@github.com:craigerl/aprsd.git
* cd aprsd
* make

Workflow
========

While working aprsd, The workflow is as follows

* checkout a new branch to work on
* git checkout -b mybranch
* Edit code
* run tox -epep8
* run tox -efmt
* run tox -p
* git commit  ( This will run the pre-commit hooks which does checks too )
* Once you are done with all of your commits, then push up the branch to
  github
* git push -u origin mybranch
* Create a pull request from your branch so github tests can run and we can do
  a code review.


Release
=======

To do release to pypi:

* Tag release with

   git tag -v1.XX -m "New release"

* push release tag up

  git push origin master --tags

* Do a test build and verify build is valid

  make build

* Once twine is happy, upload release to pypi

  make upload


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

 docker build -t hemna6969/aprsd:latest .

Development Build
=================

 docker build -t hemna6969/aprsd:latest -f Dockerfile-dev .


Running the container
=====================

There is a docker-compose.yml file that can be used to run your container.
There are 2 volumes defined that can be used to store your configuration
and the plugins directory:  /config and /plugins

If you want to install plugins at container start time, then use the
environment var in docker-compose.yml specified as APRS_PLUGINS
Provide a csv list of pypi installable plugins.  Then make sure the plugin
python file is in your /plugins volume and the plugin will be installed at
container startup.  The plugin may have dependencies that are required.
The plugin file should be copied to /plugins for loading by aprsd


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
