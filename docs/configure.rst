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

   └─[$] -> aprsd server
    Load config
    /home/aprsd/.config/aprsd/aprsd.yml is missing, creating config file
    Default config file created at /home/aprsd/.config/aprsd/aprsd.yml.  Please edit with your settings.

You can see the sample config file output

Sample config file
------------------

.. code-block:: shell

    └─[$] -> cat ~/.config/aprsd/aprsd.yml
    aprs:
      host: rotate.aprs.net
      logfile: /tmp/arsd.log
      login: someusername
      password: somepassword
      port: 14580
    aprsd:
      enabled_plugins:
      - aprsd.plugins.email.EmailPlugin
      - aprsd.plugins.fortune.FortunePlugin
      - aprsd.plugins.location.LocationPlugin
      - aprsd.plugins.ping.PingPlugin
      - aprsd.plugins.query.QueryPlugin
      - aprsd.plugins.time.TimePlugin
      - aprsd.plugins.weather.WeatherPlugin
      - aprsd.plugins.version.VersionPlugin
      plugin_dir: ~/.config/aprsd/plugins
    ham:
      callsign: KFART
    imap:
      host: imap.gmail.com
      login: imapuser
      password: something here too
      port: 993
      use_ssl: true
    shortcuts:
      aa: 5551239999@vtext.com
      cl: craiglamparter@somedomain.org
      wb: 555309@vtext.com
    smtp:
      host: imap.gmail.com
      login: something
      password: some lame password
      port: 465
      use_ssl: false


Note, You must edit the config file and change the ham callsign to your
legal FCC HAM callsign, or aprsd server will not start.

.. include:: links.rst
