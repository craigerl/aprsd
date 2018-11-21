"""Utilities and helper functions."""

import os
import pprint
import sys
import yaml

# an example of what should be in the ~/.aprsd/config.yml
example_config = '''
shortcuts:
    'aa': '5551239999@vtext.com'
    'cl': 'craiglamparter@somedomain.org'
    'wb': '555309@vtext.com'

smtp:
    login: something
    password: some lame password

imap:
    login: imapuser
    password: something dumb

ham:
    callsign: something
    basename: somebasename
'''

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
            config = yaml.load(stream)
            return config
    else:
        print("%s is missing, please create a config file" % config_file)
        print("example config is\n %s" % example_config)
        sys.exit(-1)
