"""Utilities and helper functions."""

import errno
import functools
import os
from pathlib import Path
import sys
import threading

from aprsd import plugin
import click
import yaml

# an example of what should be in the ~/.aprsd/config.yml
DEFAULT_CONFIG_DICT = {
    "ham": {"callsign": "CALLSIGN"},
    "aprs": {
        "login": "CALLSIGN",
        "password": "00000",
        "host": "rotate.aprs.net",
        "port": 14580,
        "logfile": "/tmp/aprsd.log",
    },
    "aprs.fi": {"apiKey": "set me"},
    "shortcuts": {
        "aa": "5551239999@vtext.com",
        "cl": "craiglamparter@somedomain.org",
        "wb": "555309@vtext.com",
    },
    "smtp": {
        "login": "SMTP_USERNAME",
        "password": "SMTP_PASSWORD",
        "host": "smtp.gmail.com",
        "port": 465,
        "use_ssl": False,
    },
    "imap": {
        "login": "IMAP_USERNAME",
        "password": "IMAP_PASSWORD",
        "host": "imap.gmail.com",
        "port": 993,
        "use_ssl": True,
    },
    "aprsd": {
        "plugin_dir": "~/.config/aprsd/plugins",
        "enabled_plugins": plugin.CORE_PLUGINS,
    },
}

home = str(Path.home())
DEFAULT_CONFIG_DIR = "{}/.config/aprsd/".format(home)
DEFAULT_SAVE_FILE = "{}/.config/aprsd/aprsd.p".format(home)
DEFAULT_CONFIG_FILE = "{}/.config/aprsd/aprsd.yml".format(home)


def synchronized(wrapped):
    lock = threading.Lock()

    @functools.wraps(wrapped)
    def _wrap(*args, **kwargs):
        with lock:
            return wrapped(*args, **kwargs)

    return _wrap


def env(*vars, **kwargs):
    """This returns the first environment variable set.
    if none are non-empty, defaults to '' or keyword arg default
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get("default", "")


def mkdir_p(path):
    """Make directory and have it work in py2 and py3."""
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >= 2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def insert_str(string, str_to_insert, index):
    return string[:index] + str_to_insert + string[index:]


def end_substr(original, substr):
    """Get the index of the end of the <substr>.

    So you can insert a string after <substr>
    """
    idx = original.find(substr)
    if idx != -1:
        idx += len(substr)
    return idx


def add_config_comments(raw_yaml):
    end_idx = end_substr(raw_yaml, "aprs.fi:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = insert_str(
            raw_yaml,
            "\n  # Get the apiKey from your aprs.fi account here:  http://aprs.fi/account",
            end_idx,
        )

    return raw_yaml


def create_default_config():
    """Create a default config file."""
    # make sure the directory location exists
    config_file_expanded = os.path.expanduser(DEFAULT_CONFIG_FILE)
    config_dir = os.path.dirname(config_file_expanded)
    if not os.path.exists(config_dir):
        click.echo("Config dir '{}' doesn't exist, creating.".format(config_dir))
        mkdir_p(config_dir)
    with open(config_file_expanded, "w+") as cf:
        raw_yaml = yaml.dump(DEFAULT_CONFIG_DICT)
        cf.write(add_config_comments(raw_yaml))


def get_config(config_file):
    """This tries to read the yaml config from <config_file>."""
    config_file_expanded = os.path.expanduser(config_file)
    if os.path.exists(config_file_expanded):
        with open(config_file_expanded) as stream:
            config = yaml.load(stream, Loader=yaml.FullLoader)
            return config
    else:
        if config_file == DEFAULT_CONFIG_FILE:
            click.echo(
                "{} is missing, creating config file".format(config_file_expanded),
            )
            create_default_config()
            msg = (
                "Default config file created at {}.  Please edit with your "
                "settings.".format(config_file)
            )
            click.echo(msg)
        else:
            # The user provided a config file path different from the
            # Default, so we won't try and create it, just bitch and bail.
            msg = "Custom config file '{}' is missing.".format(config_file)
            click.echo(msg)

        sys.exit(-1)


# This method tries to parse the config yaml file
# and consume the settings.
# If the required params don't exist,
# it will look in the environment
def parse_config(config_file):
    # for now we still use globals....ugh
    global CONFIG

    def fail(msg):
        click.echo(msg)
        sys.exit(-1)

    def check_option(config, section, name=None, default=None, default_fail=None):
        if section in config:

            if name and name not in config[section]:
                if not default:
                    fail(
                        "'{}' was not in '{}' section of config file".format(
                            name,
                            section,
                        ),
                    )
                else:
                    config[section][name] = default
            else:
                if (
                    default_fail
                    and name in config[section]
                    and config[section][name] == default_fail
                ):
                    # We have to fail and bail if the user hasn't edited
                    # this config option.
                    fail("Config file needs to be edited from provided defaults.")
        else:
            fail("'%s' section wasn't in config file" % section)
        return config

    config = get_config(config_file)
    check_option(config, "shortcuts")
    # special check here to make sure user has edited the config file
    # and changed the ham callsign
    check_option(
        config,
        "ham",
        "callsign",
        default_fail=DEFAULT_CONFIG_DICT["ham"]["callsign"],
    )
    check_option(
        config,
        "aprs.fi",
        "apiKey",
        default_fail=DEFAULT_CONFIG_DICT["aprs.fi"]["apiKey"],
    )
    check_option(config, "aprs", "login")
    check_option(config, "aprs", "password")
    # check_option(config, "aprs", "host")
    # check_option(config, "aprs", "port")
    check_option(config, "aprs", "logfile", "./aprsd.log")
    check_option(config, "imap", "host")
    check_option(config, "imap", "login")
    check_option(config, "imap", "password")
    check_option(config, "smtp", "host")
    check_option(config, "smtp", "port")
    check_option(config, "smtp", "login")
    check_option(config, "smtp", "password")

    return config
