"""Utilities and helper functions."""

import logging
import os
import sys
import yaml

# an example of what should be in the ~/.aprsd/config.yml
example_config = '''
ham:
    callsign: KFART

aprs:
    login: someusername
    password: password
    host: noam.aprs2.net
    port: 14580
    logfile: /tmp/aprsd.log

shortcuts:
    'aa': '5551239999@vtext.com'
    'cl': 'craiglamparter@somedomain.org'
    'wb': '555309@vtext.com'

smtp:
    login: something
    password: some lame password
    host: imap.gmail.com
    port: 465

imap:
    login: imapuser
    password: something dumb
    host: imap.gmail.com
'''

log = logging.getLogger('APRSD')


def env(*vars, **kwargs):
    """This returns the first environment variable set.
    if none are non-empty, defaults to '' or keyword arg default
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')


def get_config():
    """This tries to read the yaml config from ~/.aprsd/config.yml."""
    config_file = os.path.expanduser("~/.aprsd/config.yml")
    if os.path.exists(config_file):
        with open(config_file, "r") as stream:
            config = yaml.load(stream, Loader=yaml.FullLoader)
            return config
    else:
        log.critical("%s is missing, please create config file" % config_file)
        print("\nCopy to ~/.aprsd/config.yml and edit\n\nSample config:\n %s"
              % example_config)
        sys.exit(-1)


# This method tries to parse the config yaml file
# and consume the settings.
# If the required params don't exist,
# it will look in the environment
def parse_config(args):
    # for now we still use globals....ugh
    global CONFIG, LOG

    def fail(msg):
        LOG.critical(msg)
        sys.exit(-1)

    def check_option(config, section, name=None, default=None):
        if section in config:
            if name and name not in config[section]:
                if not default:
                    fail("'%s' was not in '%s' section of config file" %
                         (name, section))
                else:
                    config[section][name] = default
        else:
            fail("'%s' section wasn't in config file" % section)
        return config

    # Now read the ~/.aprds/config.yml
    config = get_config()
    check_option(config, 'shortcuts')
    check_option(config, 'ham', 'callsign')
    check_option(config, 'aprs', 'login')
    check_option(config, 'aprs', 'password')
    check_option(config, 'aprs', 'host')
    check_option(config, 'aprs', 'port')
    config = check_option(config, 'aprs', 'logfile', './aprsd.log')
    check_option(config, 'imap', 'host')
    check_option(config, 'imap', 'login')
    check_option(config, 'imap', 'password')
    check_option(config, 'smtp', 'host')
    check_option(config, 'smtp', 'port')
    check_option(config, 'smtp', 'login')
    check_option(config, 'smtp', 'password')

    return config
    LOG.info("aprsd config loaded")
