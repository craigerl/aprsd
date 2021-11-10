import collections
import logging
import os
from pathlib import Path
import sys

import click
import yaml

from aprsd import utils


home = str(Path.home())
DEFAULT_CONFIG_DIR = f"{home}/.config/aprsd/"
DEFAULT_SAVE_FILE = f"{home}/.config/aprsd/aprsd.p"
DEFAULT_CONFIG_FILE = f"{home}/.config/aprsd/aprsd.yml"


LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

DEFAULT_DATE_FORMAT = "%m/%d/%Y %I:%M:%S %p"
DEFAULT_LOG_FORMAT = (
    "[%(asctime)s] [%(threadName)-20.20s] [%(levelname)-5.5s]"
    " %(message)s - [%(pathname)s:%(lineno)d]"
)

QUEUE_DATE_FORMAT = "[%m/%d/%Y] [%I:%M:%S %p]"
QUEUE_LOG_FORMAT = (
    "%(asctime)s [%(threadName)-20.20s] [%(levelname)-5.5s]"
    " %(message)s - [%(pathname)s:%(lineno)d]"
)

CORE_MESSAGE_PLUGINS = [
    "aprsd.plugins.email.EmailPlugin",
    "aprsd.plugins.fortune.FortunePlugin",
    "aprsd.plugins.location.LocationPlugin",
    "aprsd.plugins.ping.PingPlugin",
    "aprsd.plugins.query.QueryPlugin",
    "aprsd.plugins.stock.StockPlugin",
    "aprsd.plugins.time.TimePlugin",
    "aprsd.plugins.weather.USWeatherPlugin",
    "aprsd.plugins.version.VersionPlugin",
]

CORE_NOTIFY_PLUGINS = [
    "aprsd.plugins.notify.NotifySeenPlugin",
]

# an example of what should be in the ~/.aprsd/config.yml
DEFAULT_CONFIG_DICT = {
    "ham": {"callsign": "NOCALL"},
    "aprs": {
        "enabled": True,
        "login": "CALLSIGN",
        "password": "00000",
        "host": "rotate.aprs2.net",
        "port": 14580,
    },
    "kiss": {
        "tcp": {
            "enabled": False,
            "host": "direwolf.ip.address",
            "port": "8001",
        },
        "serial": {
            "enabled": False,
            "device": "/dev/ttyS0",
            "baudrate": 9600,
        },
    },
    "aprsd": {
        "logfile": "/tmp/aprsd.log",
        "logformat": DEFAULT_LOG_FORMAT,
        "dateformat": DEFAULT_DATE_FORMAT,
        "save_location": DEFAULT_CONFIG_DIR,
        "trace": False,
        "enabled_plugins": CORE_MESSAGE_PLUGINS,
        "units": "imperial",
        "watch_list": {
            "enabled": False,
            # Who gets the alert?
            "alert_callsign": "NOCALL",
            # 43200 is 12 hours
            "alert_time_seconds": 43200,
            # How many packets to save in a ring Buffer
            # for a particular callsign
            "packet_keep_count": 10,
            "callsigns": [],
            "enabled_plugins": CORE_NOTIFY_PLUGINS,
        },
        "web": {
            "enabled": True,
            "logging_enabled": True,
            "host": "0.0.0.0",
            "port": 8001,
            "users": {
                "admin": "password-here",
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


class Config(collections.UserDict):
    def _get(self, d, keys, default=None):
        """
        Example:
            d = {'meta': {'status': 'OK', 'status_code': 200}}
            _get(d, ['meta', 'status_code'])          # => 200
            _get(d, ['garbage', 'status_code'])       # => None
            _get(d, ['meta', 'garbage'], default='-') # => '-'

        """
        if type(keys) is str and "." in keys:
            keys = keys.split(".")

        assert type(keys) is list
        if d is None:
            return default

        if not keys:
            return d

        if type(d) is str:
            return default

        return self._get(d.get(keys[0]), keys[1:], default)

    def get(self, path, default=None):
        return self._get(self.data, path, default=default)

    def exists(self, path):
        """See if a conf value exists."""
        test = "-3.14TEST41.3-"
        return self.get(path, default=test) != test

    def check_option(self, path, default_fail=None):
        """Make sure the config option doesn't have default value."""
        if not self.exists(path):
            raise Exception(
                "Option '{}' was not in config file".format(
                    path,
                ),
            )

        val = self.get(path)
        if val == default_fail:
            # We have to fail and bail if the user hasn't edited
            # this config option.
            raise Exception(
                "Config file needs to be changed from provided"
                " defaults for '{}'".format(
                    path,
                ),
            )


def add_config_comments(raw_yaml):
    end_idx = utils.end_substr(raw_yaml, "aprs:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = utils.insert_str(
            raw_yaml,
            "\n    # Set enabled to False if there is no internet connectivity."
            "\n    # This is useful for a direwolf KISS aprs connection only. "
            "\n"
            "\n    # Get the passcode for your callsign here: "
            "\n    # https://apps.magicbug.co.uk/passcode",
            end_idx,
        )

    end_idx = utils.end_substr(raw_yaml, "aprs.fi:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = utils.insert_str(
            raw_yaml,
            "\n        # Get the apiKey from your aprs.fi account here:  "
            "\n        # http://aprs.fi/account",
            end_idx,
        )

    end_idx = utils.end_substr(raw_yaml, "opencagedata:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = utils.insert_str(
            raw_yaml,
            "\n        # (Optional for TimeOpenCageDataPlugin) "
            "\n        # Get the apiKey from your opencagedata account here:  "
            "\n        # https://opencagedata.com/dashboard#api-keys",
            end_idx,
        )

    end_idx = utils.end_substr(raw_yaml, "openweathermap:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = utils.insert_str(
            raw_yaml,
            "\n        # (Optional for OWMWeatherPlugin) "
            "\n        # Get the apiKey from your "
            "\n        # openweathermap account here: "
            "\n        # https://home.openweathermap.org/api_keys",
            end_idx,
        )

    end_idx = utils.end_substr(raw_yaml, "avwx:")
    if end_idx != -1:
        # lets insert a comment
        raw_yaml = utils.insert_str(
            raw_yaml,
            "\n        # (Optional for AVWXWeatherPlugin) "
            "\n        # Use hosted avwx-api here: https://avwx.rest "
            "\n        # or deploy your own from here: "
            "\n        # https://github.com/avwx-rest/avwx-api",
            end_idx,
        )

    return raw_yaml


def dump_default_cfg():
    return add_config_comments(
        yaml.dump(
            DEFAULT_CONFIG_DICT,
            indent=4,
        ),
    )


def create_default_config():
    """Create a default config file."""
    # make sure the directory location exists
    config_file_expanded = os.path.expanduser(DEFAULT_CONFIG_FILE)
    config_dir = os.path.dirname(config_file_expanded)
    if not os.path.exists(config_dir):
        click.echo(f"Config dir '{config_dir}' doesn't exist, creating.")
        utils.mkdir_p(config_dir)
    with open(config_file_expanded, "w+") as cf:
        cf.write(dump_default_cfg())


def get_config(config_file):
    """This tries to read the yaml config from <config_file>."""
    config_file_expanded = os.path.expanduser(config_file)
    if os.path.exists(config_file_expanded):
        with open(config_file_expanded) as stream:
            config = yaml.load(stream, Loader=yaml.FullLoader)
            return Config(config)
    else:
        if config_file == DEFAULT_CONFIG_FILE:
            click.echo(
                f"{config_file_expanded} is missing, creating config file",
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
            msg = f"Custom config file '{config_file}' is missing."
            click.echo(msg)

        sys.exit(-1)


# This method tries to parse the config yaml file
# and consume the settings.
# If the required params don't exist,
# it will look in the environment
def parse_config(config_file):
    config = get_config(config_file)

    def fail(msg):
        click.echo(msg)
        sys.exit(-1)

    def check_option(config, path, default_fail=None):
        try:
            config.check_option(path, default_fail=default_fail)
        except Exception as ex:
            fail(repr(ex))
        else:
            return config

    # special check here to make sure user has edited the config file
    # and changed the ham callsign
    check_option(
        config,
        "ham.callsign",
        default_fail=DEFAULT_CONFIG_DICT["ham"]["callsign"],
    )
    check_option(
        config,
        "aprs.login",
        default_fail=DEFAULT_CONFIG_DICT["aprs"]["login"],
    )
    check_option(
        config,
        ["aprs", "password"],
        default_fail=DEFAULT_CONFIG_DICT["aprs"]["password"],
    )

    # Ensure they change the admin password
    if config.get("aprsd.web.enabled") is True:
        check_option(
            config,
            ["aprsd", "web", "users", "admin"],
            default_fail=DEFAULT_CONFIG_DICT["aprsd"]["web"]["users"]["admin"],
        )

    if config.get("aprsd.watch_list.enabled") is True:
        check_option(
            config,
            ["aprsd", "watch_list", "alert_callsign"],
            default_fail=DEFAULT_CONFIG_DICT["aprsd"]["watch_list"]["alert_callsign"],
        )

    if config.get("aprsd.email.enabled") is True:
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
