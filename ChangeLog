CHANGES
=======

* Decouple admin web interface from server command
* Dockerfile now produces aprsd.conf
* Fix some unit tests and loading of CONF w/o file
* Added missing conf
* Removed references to old custom config
* Convert config to oslo\_config
* Added rain formatting unit tests to WeatherPacket
* Fix Rain reporting in WeatherPacket send
* Removed Packet.send()
* Removed watchlist plugins
* Fix PluginManager.get\_plugins
* Cleaned up PluginManager
* Cleaned up PluginManager
* Update routing for weatherpacket
* Fix some WeatherPacket formatting
* Fix pep8 violation
* Add packet filtering for aprsd listen
* Added WeatherPacket encoding
* Updated webchat and listen for queue based RX
* reworked collecting and reporting stats
* Removed unused threading code
* Change RX packet processing to enqueu
* Make tracking objectstores work w/o initializing
* Cleaned up packet transmit class attributes
* Fix packets timestamp to int
* More messaging -> packets cleanup
* Cleaned out all references to messaging
* Added contructing a GPSPacket for sending
* cleanup webchat
* Reworked all packet processing
* Updated plugins and plugin interfaces for Packet
* Started using dataclasses to describe packets

v2.6.1
------

* v2.6.1
* Fixed position report for webchat beacon
* Try and fix broken 32bit qemu builds on 64bit system
* Add unit tests for webchat
* remove armv7 build RUST sucks
* Fix for Collections change in 3.10

v2.6.0
------

* Update workflow again
* Update Dockerfile to 22.04
* Update Dockerfile and build.sh
* Update workflow
* Prep for 2.6.0 release
* Update requirements
* Removed Makefile comment
* Update Makefile for dev vs. run environments
* Added pyopenssl for https for webchat
* change from device-detector to user-agents
* Remove twine from dev-requirements
* Update to latest Makefile.venv
* Refactored threads a bit
* Mark packets as acked in MsgTracker
* remove dev setting for template
* Add GPS beacon to mobile page
* Allow werkzeug for admin interface
* Allow werkzeug for admin interface
* Add support for mobile browsers for webchat
* Ignore callsign case while processing packets
* remove linux/arm/v7 for official builds for now
* added workflow for building specific version
* Allow passing in version to the Dockerfile
* Send GPS Beacon from webchat interface
* specify Dockerfile-dev
* Fixed build.sh
* Build on the source not released aprsd
* Remove email validation
* Add support for building linux/arm/v7
* Remove python 3.7 from docker build github
* Fixed failing unit tests
* change github workflow
* Removed TimeOpenCageDataPlugin
* Dump config with aprsd dev test-plugin
* Updated requirements
* Got webchat working with KISS tcp
* Added click auto\_envvar\_prefix
* Update aprsd thread base class to use queue
* Update packets to use wrapt
* Add remving existing requirements
* Try sending raw APRSFrames to aioax25
* Use new aprsd.callsign as the main callsign
* Fixed access to threads refactor
* Added webchat command
* Moved log.py to logging
* Moved trace.py to utils
* Fixed pep8 errors
* Refactored threads.py
* Refactor utils to directory
* remove arm build for now
* Added rustc and cargo to Dockerfile
* remove linux/arm/v6 from docker platform build
* Only tag master build as master
* Remove docker build from test
* create master-build.yml
* Added container build action
* Update docs on using Docker
* Update dev-requirements pip-tools
* Fix typo in docker-compose.yml
* Fix PyPI scraping
* Allow web interface when running in Docker
* Fix typo on exception
* README formatting fixes
* Bump dependencies to fix python 3.10
* Fixed up config option checking for KISS
* Fix logging issue with log messages
* for 2.5.9

v2.5.9
------

* FIX: logging exceptions
* Updated build and run for rich lib
* update build for 2.5.8

v2.5.8
------

* For 2.5.8
* Removed debug code
* Updated list-plugins
* Renamed virtualenv dir to .aprsd-venv
* Added unit tests for dev test-plugin
* Send Message command defaults to config

v2.5.7
------

* Updated Changelog
* Fixed an KISS config disabled issue
* Fixed a bug with multiple notify plugins enabled
* Unify the logging to file and stdout
* Added new feature to list-plugins command
* more README.rst cleanup
* Updated README examples

v2.5.6
------

* Changelog
* Tightened up the packet logging
* Added unit tests for USWeatherPlugin, USMetarPlugin
* Added test\_location to test LocationPlugin
* Updated pytest output
* Added py39 to tox for tests
* Added NotifyPlugin unit tests and more
* Small cleanup on packet logging
* Reduced the APRSIS connection reset to 2 minutes
* Fixed the NotifyPlugin
* Fixed some pep8 errors
* Add tracing for dev command
* Added python rich library based logging
* Added LOG\_LEVEL env variable for the docker

v2.5.5
------

* Update requirements to use aprslib 0.7.0
* fixed the failure during loading for objectstore
* updated docker build

v2.5.4
------

* Updated Changelog
* Fixed dev command missing initialization

v2.5.3
------

* Fix admin logging tab

v2.5.2
------

* Added new list-plugins command
* Don't require check-version command to have a config
* Healthcheck command doesn't need the aprsd.yml config
* Fix test failures
* Removed requirement for aprs.fi key
* Updated Changelog

v2.5.1
------

* Removed stock plugin
* Removed the stock plugin

v2.5.0
------

* Updated for v2.5.0
* Updated Dockerfile's and build script for docker
* Cleaned up some verbose output & colorized output
* Reworked all the common arguments
* Fixed test-plugin
* Ensure common params are honored
* pep8
* Added healthcheck to the cmds
* Removed the need for FROMCALL in dev test-plugin
* Pep8 failures
* Refactor the cli
* Updated Changelog for 4.2.3
* Fixed a problem with send-message command

v2.4.2
------

* Updated Changelog
* Be more careful picking data to/from disk
* Updated Changelog

v2.4.1
------

* Ensure plugins are last to be loaded
* Fixed email connecting to smtp server

v2.4.0
------

* Updated Changelog for 2.4.0 release
* Converted MsgTrack to ObjectStoreMixin
* Fixed unit tests
* Make sure SeenList update has a from in packet
* Ensure PacketList is initialized
* Added SIGTERM to signal\_handler
* Enable configuring where to save the objectstore data
* PEP8 cleanup
* Added objectstore Mixin
* Added -num option to aprsd-dev test-plugin
* Only call stop\_threads if it exists
* Added new SeenList
* Added plugin version to stats reporting
* Added new HelpPlugin
* Updated aprsd-dev to use config for logfile format
* Updated build.sh
* removed usage of config.check\_config\_option
* Fixed send-message after config/client rework
* Fixed issue with flask config
* Added some server startup info logs
* Increase email delay to +10
* Updated dev to use plugin manager
* Fixed notify plugins
* Added new Config object
* Fixed email plugin's use of globals
* Refactored client classes
* Refactor utils usage
* 2.3.1 Changelog

v2.3.1
------

* Fixed issue of aprs-is missing keepalive
* Fixed packet processing issue with aprsd send-message

v2.3.0
------

* Prep 2.3.0
* Enable plugins to return message object
* Added enabled flag for every plugin object
* Ensure plugin threads are valid
* Updated Dockerfile to use v2.3.0
* Removed fixed size on logging queue
* Added Logfile tab in Admin ui
* Updated Makefile clean target
* Added self creating Makefile help target
* Update dev.py
* Allow passing in aprsis\_client
* Fixed a problem with the AVWX plugin not working
* Remove some noisy trace in email plugin
* Fixed issue at startup with notify plugin
* Fixed email validation
* Removed values from forms
* Added send-message to the main admin UI
* Updated requirements
* Cleaned up some pep8 failures
* Upgraded the send-message POC to use websockets
* New Admin ui send message page working
* Send Message via admin Web interface
* Updated Admin UI to show KISS connections
* Got TX/RX working with aioax25+direwolf over TCP
* Rebased from master
* Added the ability to use direwolf KISS socket
* Update Dockerfile to use 2.2.1

v2.2.1
------

* Update Changelog for 2.2.1
* Silence some log noise

v2.2.0
------

* Updated Changelog for v2.2.0
* Updated overview image
* Removed Black code style reference
* Removed TXThread
* Added days to uptime string formatting
* Updated select timeouts
* Rebase from master and run gray
* Added tracking plugin processing
* Added threads functions to APRSDPluginBase
* Refactor Message processing and MORE
* Use Gray instead of Black for code formatting
* Updated tox.ini
* Fixed LOG.debug issue in weather plugin
* Updated slack channel link
* Cleanup of the README.rst
* Fixed aprsd-dev

v2.1.0
------

* Prep for v2.1.0
* Enable multiple replies for plugins
* Put in a fix for aprslib parse exceptions
* Fixed time plugin
* Updated the charts Added the packets chart
* Added showing symbol images to watch list

v2.0.0
------

* Updated docs for 2.0.0
* Reworked the notification threads and admin ui
* Fixed small bug with packets get\_packet\_type
* Updated overview images
* Move version string output to top of log
* Add new watchlist feature
* Fixed the Ack thread not resending acks
* reworked the admin ui to use semenatic ui more
* Added messages count to admin messages list
* Add admin UI tabs for charts, messages, config
* Removed a noisy debug log
* Dump out the config during startup
* Added message counts for each plugin
* Bump urllib3 from 1.26.4 to 1.26.5
* Added aprsd version checking
* Updated INSTALL.txt
* Update my callsign
* Update README.rst
* Update README.rst
* Bump urllib3 from 1.26.3 to 1.26.4
* Prep for v1.6.1 release

v1.6.1
------

* Removed debug log for KeepAlive thread
* ignore Makefile.venv
* Reworked Makefile to use Makefile.venv
* Fixed version unit tests
* Updated stats output for KeepAlive thread
* Update Dockerfile-dev to work with startup
* Force all the graphs to 0 minimum
* Added email messages graphs
* Reworked the stats dict output and healthcheck
* Added callsign to the web index page
* Added log config for flask and lnav config file
* Added showing APRS-IS server to stats
* Provide an initial datapoint on rendering index
* Make the index page behind auth
* Bump pygments from 2.7.3 to 2.7.4
* Added acks with messages graphs
* Updated web stats index to show messages and ram usage
* Added aprsd web index page
* Bump lxml from 4.6.2 to 4.6.3
* Bump jinja2 from 2.11.2 to 2.11.3
* Bump urllib3 from 1.26.2 to 1.26.3
* Added log format and dateformat to config file
* Added Dockerfile-dev and updated build.sh
* Require python 3.7 and >
* Added plugin live reload and StockPlugin
* Updated Dockerfile and build.sh
* Updated Dockerfile for multiplatform builds
* Updated Dockerfile for multiplatform builds
* Dockerfile: Make creation of /config quiet failure
* Updated README docs

v1.6.0
------

* 1.6.0 release prep
* Updated path of run.sh for docker build
* Moved docker related stuffs to docker dir
* Removed some noisy debug log
* Bump cryptography from 3.3.1 to 3.3.2
* Wrap another server call with try except
* Wrap all imap calls with try except blocks
* Bump bleach from 3.2.1 to 3.3.0
* EmailThread was exiting because of IMAP timeout, added exceptions for this
* Added memory tracing in keeplive
* Fixed tox pep8 failure for trace
* Added tracing facility
* Fixed email login issue
* duplicate email messages from RF would generate usage response
* Enable debug logging for smtp and imap
* more debug around email thread
* debug around EmailThread hanging or vanishing
* Fixed resend email after config rework
* Added flask messages web UI and basic auth
* Fixed an issue with LocationPlugin
* Cleaned up the KeepAlive output
* updated .gitignore
* Added healthcheck app
* Add flask and flask\_classful reqs
* Added Flask web thread and stats collection
* First hack at flask
* Allow email to be disabled
* Reworked the config file and options
* Updated documentation and config output
* Fixed extracting lat/lon
* Added openweathermap weather plugin
* Added new time plugins
* Fixed TimePlugin timezone issue
* remove fortune white space
* fix git with install.txt
* change query char from ? to !
* Updated readme to include readthedocs link
* Added aprsd-dev plugin test cli and WxPlugin

v1.5.1
------

* Updated Changelog for v1.5.1
* Updated README to fix pypi page
* Update INSTALL.txt

v1.5.0
------

* Updated Changelog for v1.5.0 release
* Fix tox tests
* fix usage statement
* Enabled some emailthread messages and added timestamp
* Fixed main server client initialization
* test plugin expect responses update to match query output
* Fixed the queryPlugin unit test
* Removed flask code
* Changed default log level to INFO
* fix plugin tests to expect new strings
* fix query command syntax  ?,  ?3,  ?d(elete),  ?a(ll)
* Fixed latitude reporting in locationPlugin
* get rid of some debug noise from tracker and email delay
* fixed sample-config double print
* make sample config easier to interpret
* Fixed comments
* Added the ability to add comments to the config file
* Updated docker run.sh script
* Added --raw format for sending messages
* Fixed --quiet option
* Added send-message login checking and --no-ack
* Added new config for aprs.fi API Key
* Added a fix for failed logins to APRS-IS
* Fixed unit test for fortune plugin
* Fixed fortune plugin failures
* getting out of git hell with client.py problems
* Extend APRS.IS object to change login string
* Extend APRS.IS object to change login string
* expect different reply from query plugin
* update query plugin to resend last N messages. syntax:  ?rN
* Added unit test for QueryPlugin
* Updated MsgTrack restart\_delayed
* refactor Plugin objects to plugins directory
* Updated README with more workflow details
* change query character syntax, don't reply that we're resending stuff
* Added APRSD system diagram to docs
* Disable MX record validation
* Added some more badges to readme files
* Updated build for docs  tox -edocs
* switch command characters for query plugin
* Fix broken test
* undo git disaster
* swap Query command characters a bit
* Added Sphinx based documentation
* refactor Plugin objects to plugins directory
* Updated Makefile
* removed double-quote-string-fixer
* Lots of fixes
* Added more pre-commit hook tests
* Fixed email shortcut lookup
* Added Makefile for easy dev setup
* Added Makefile for easy dev setup
* Cleaned out old ack\_dict
* add null reply for send\_email
* Updated README with more workflow details
* backout my patch that broke tox, trying to push to craiger-test branch
* Fixed failures caused by last commit
* don't tell radio emails were sent, ack is enuf
* Updated README to include development env
* Added pre-commit hooks
* Update Changelog for v1.5.0
* Added QueryPlugin resend all delayed msgs or Flush
* Added QueryPlugin
* Added support to save/load MsgTrack on exit/start
* Creation of MsgTrack object and other stuff
* Added FortunePlugin unit test
* Added some plugin unit tests
* reworked threading
* Reworked messaging lib

v1.1.0
------

* Refactored the main process\_packet method
* Update README with version 1.1.0 related info
* Added fix for an unknown packet type
* Ensure fortune is installed
* Updated docker-compose
* Added Changelog
* Fixed issue when RX ack
* Updated the aprsd-slack-plugin required version
* Updated README.rst
* Fixed send-message with email command and others
* Update .gitignore
* Big patch
* Major refactor
* Updated the Dockerfile to use alpine

v1.0.1
------

* Fix unknown characterset emails
* Updated loggin timestamp to include []
* Updated README with a TOC
* Updates for building containers
* Don't use the dirname for the plugin path search
* Reworked Plugin loading
* Updated README with development information
* Fixed an issue with weather plugin

v1.0.0
------

* Rewrote the README.md to README.rst
* Fixed the usage string after plugins introduced
* Created plugin.py for Command Plugins
* Refactor networking and commands
* get rid of some debug statements
* yet another unicode problem, in resend\_email fixed
* reset default email check delay to 60, fix a few comments
* Update tox environment to fix formatting python errors
* fixed fortune. yet another unicode issue, tested in py3 and py2
* lose some logging statements
* completely off urllib now, tested locate/weather in py2 and py3
* add urllib import back until i replace all calls with requests
* cleaned up weather code after switch to requests ... from urllib. works on py2 and py3
* switch from urlib to requests for weather, tested in py3 and py2.  still need to update locate, and all other http calls
* imap tags are unicode in py3.  .decode tags
* Update INSTALL.txt
* Initial conversion to click
* Reconnect on socket timeout
* clean up code around closed\_socket and reconnect
* Update INSTALL.txt
* Fixed all pep8 errors and some py3 errors
* fix check\_email\_thread to do proper threading, take delay as arg
* found another .decode that didn't include errors='ignore'
* some failed attempts at getting the first txt or html from a multipart message, currently sends the last
* fix parse\_email unicode probs by using body.decode(errors='ignore').. again
* fix parse\_email unicode probs by using body.decode(errors='ignore')
* clean up code around closed\_socket and reconnect
* socket timeout 5 minutes
* Detect closed socket, reconnect, with a bit more grace
* can detect closed socket and reconnect now
* Update INSTALL.txt
* more debugging messages trying to find rare tight loop in main
* Update INSTALL.txt
* main loop went into tight loop, more debug prints
* main loop went into tight loop, added debug print before every continue
* Update INSTALL.txt
* Update INSTALL.txt
* George Carlin profanity filter
* added decaying email check timer which resets with activity
* Fixed all pep8 errors and some py3 errors
* Fixed all pep8 errors and some py3 errors
* Reconnect on socket timeout
* socket reconnect on timeout testing
* socket timeout of 300 instead of 60
* Reconnect on socket timeout
* socket reconnect on timeout testing
* Fixed all pep8 errors and some py3 errors
* fix check\_email\_thread to do proper threading, take delay as arg
* INSTALL.txt for the average person
* fix bugs after beautification and yaml config additions. Convert to sockets.  case insensitive commands
* fix INBOX
* Update README.md
* Added tox support
* Fixed SMTP settings
* Created fake\_aprs.py
* select inbox if gmail server
* removed ASS
* Added a try block around imap login
* Added port and fixed telnet user
* Require ~/.aprsd/config.yml
* updated README for install and usage instructions
* added test to ensure shortcuts in config.yml
* added exit if missing config file
* Added reading of a config file
* update readme
* update readme
* sanitize readme
* readme again again
* readme again again
* readme again
* readme
* readme update
* First stab at migrating this to a pytpi repo
* First stab at migrating this to a pytpi repo
* Added password, callsign and host
* Added argparse for cli options
* comments
* Cleaned up trailing whitespace
* add tweaked fuzzyclock
* make tn a global
* Added standard python main()
* tweaks to readme
* drop virtenv on first line
* sanitize readme a bit more
* sanitize readme a bit more
* sanitize readme
* added weather and location 3
* added weather and location 2
* added weather and location
* mapme
* de-localize
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* de-localize
* Update README.md
* Update README.md
* Update aprsd.py
* Add files via upload
* Update README.md
* Update aprsd.py
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* Update README.md
* Add files via upload
* Initial commit
