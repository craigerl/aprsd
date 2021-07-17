CHANGES
=======

v2.0.0
------

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
