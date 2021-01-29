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
        "host": "rotate.aprs2.net",
        "port": 14580,
    },
    "aprsd": {
        "logfile": "/tmp/aprsd.log",
        "trace": False,
        "plugin_dir": "~/.config/aprsd/plugins",
        "enabled_plugins": plugin.CORE_PLUGINS,
        "units": "imperial",
        "web": {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 8001,
            "users": {
                "admin": "aprsd",
            },
        },
        "email": {
            "enabled": True,
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
                "debug": False,
            },
            "imap": {
                "login": "IMAP_USERNAME",
                "password": "IMAP_PASSWORD",
                "host": "imap.gmail.com",
                "port": 993,
                "use_ssl": True,
                "debug": False,
            },
        },
    },
    "services": {
        "aprs.fi": {"apiKey": "APIKEYVALUE"},
        "openweathermap": {"apiKey": "APIKEYVALUE"},
        "opencagedata": {"apiKey": "APIKEYVALUE"},
        "avwx": {"base_url": "http://host:port", "apiKey": "APIKEYVALUE"},
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


def dump_default_cfg():
    return add_config_comments(
        yaml.dump(
            DEFAULT_CONFIG_DICT,
            indent=4,
        ),
    )


def add_config_comments(raw_yaml):
    end_idx = end_substr(raw_yaml, "aprs:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = insert_str(
            raw_yaml,
            "\n    # Get the passcode for your callsign here: "
            "\n    # https://apps.magicbug.co.uk/passcode",
            end_idx,
        )

    end_idx = end_substr(raw_yaml, "aprs.fi:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = insert_str(
            raw_yaml,
            "\n        # Get the apiKey from your aprs.fi account here:  "
            "\n        # http://aprs.fi/account",
            end_idx,
        )

    end_idx = end_substr(raw_yaml, "opencagedata:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = insert_str(
            raw_yaml,
            "\n        # (Optional for TimeOpenCageDataPlugin) "
            "\n        # Get the apiKey from your opencagedata account here:  "
            "\n        # https://opencagedata.com/dashboard#api-keys",
            end_idx,
        )

    end_idx = end_substr(raw_yaml, "openweathermap:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = insert_str(
            raw_yaml,
            "\n        # (Optional for OWMWeatherPlugin) "
            "\n        # Get the apiKey from your "
            "\n        # openweathermap account here: "
            "\n        # https://home.openweathermap.org/api_keys",
            end_idx,
        )

    end_idx = end_substr(raw_yaml, "avwx:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = insert_str(
            raw_yaml,
            "\n        # (Optional for AVWXWeatherPlugin) "
            "\n        # Use hosted avwx-api here: https://avwx.rest "
            "\n        # or deploy your own from here: "
            "\n        # https://github.com/avwx-rest/avwx-api",
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
        cf.write(dump_default_cfg())


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


def conf_option_exists(conf, chain):
    _key = chain.pop(0)
    if _key in conf:
        return conf_option_exists(conf[_key], chain) if chain else conf[_key]


def check_config_option(config, chain, default_fail=None):
    result = conf_option_exists(config, chain.copy())
    if not result:
        raise Exception(
            "'{}' was not in config file".format(
                chain,
            ),
        )
    else:
        if default_fail:
            if result == default_fail:
                # We have to fail and bail if the user hasn't edited
                # this config option.
                raise Exception(
                    "Config file needs to be edited from provided defaults for {}.".format(
                        chain,
                    ),
                )
        else:
            return config


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

    def check_option(config, chain, default_fail=None):
        try:
            config = check_config_option(config, chain, default_fail=default_fail)
        except Exception as ex:
            fail(repr(ex))
        else:
            return config

    config = get_config(config_file)

    # special check here to make sure user has edited the config file
    # and changed the ham callsign
    check_option(
        config,
        [
            "ham",
            "callsign",
        ],
        default_fail=DEFAULT_CONFIG_DICT["ham"]["callsign"],
    )
    check_option(
        config,
        ["services", "aprs.fi", "apiKey"],
        default_fail=DEFAULT_CONFIG_DICT["services"]["aprs.fi"]["apiKey"],
    )
    check_option(
        config,
        ["aprs", "login"],
        default_fail=DEFAULT_CONFIG_DICT["aprs"]["login"],
    )
    check_option(
        config,
        ["aprs", "password"],
        default_fail=DEFAULT_CONFIG_DICT["aprs"]["password"],
    )

    # Ensure they change the admin password
    if config["aprsd"]["web"]["enabled"] is True:
        check_option(
            config,
            ["aprsd", "web", "users", "admin"],
            default_fail=DEFAULT_CONFIG_DICT["aprsd"]["web"]["users"]["admin"],
        )

    if config["aprsd"]["email"]["enabled"] is True:
        # Check IMAP server settings
        check_option(config, ["aprsd", "email", "imap", "host"])
        check_option(config, ["aprsd", "email", "imap", "port"])
        check_option(
            config,
            ["aprsd", "email", "imap", "login"],
            default_fail=DEFAULT_CONFIG_DICT["aprsd"]["email"]["imap"]["login"],
        )
        check_option(
            config,
            ["aprsd", "email", "imap", "password"],
            default_fail=DEFAULT_CONFIG_DICT["aprsd"]["email"]["imap"]["password"],
        )

        # Check SMTP server settings
        check_option(config, ["aprsd", "email", "smtp", "host"])
        check_option(config, ["aprsd", "email", "smtp", "port"])
        check_option(
            config,
            ["aprsd", "email", "smtp", "login"],
            default_fail=DEFAULT_CONFIG_DICT["aprsd"]["email"]["smtp"]["login"],
        )
        check_option(
            config,
            ["aprsd", "email", "smtp", "password"],
            default_fail=DEFAULT_CONFIG_DICT["aprsd"]["email"]["smtp"]["password"],
        )

    return config
