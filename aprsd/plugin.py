# The base plugin class
import abc
import fnmatch
import imp
import inspect
import json
import logging
import os
import re
import subprocess
import time

import pluggy
import requests
import six

from aprsd.fuzzyclock import fuzzy

# setup the global logger
LOG = logging.getLogger("APRSD")

hookspec = pluggy.HookspecMarker("aprsd")
hookimpl = pluggy.HookimplMarker("aprsd")

CORE_PLUGINS = [
    "FortunePlugin",
    "LocationPlugin",
    "PingPlugin",
    "TimePlugin",
    "WeatherPlugin",
]


def setup_plugins(config):
    """Create the plugin manager and register plugins."""

    LOG.info("Loading Core APRSD Command Plugins")
    enabled_plugins = config["aprsd"].get("enabled_plugins", None)
    pm = pluggy.PluginManager("aprsd")
    pm.add_hookspecs(APRSDCommandSpec)
    for p_name in CORE_PLUGINS:
        plugin_obj = None
        if enabled_plugins:
            if p_name in enabled_plugins:
                plugin_obj = globals()[p_name](config)
        else:
            # Enabled plugins isn't set, so we default to loading all of
            # the core plugins.
            plugin_obj = globals()[p_name](config)

        if plugin_obj:
            LOG.info(
                "Registering Command plugin '{}'({})  '{}'".format(
                    p_name, plugin_obj.version, plugin_obj.command_regex
                )
            )
            pm.register(plugin_obj)

    plugin_dir = config["aprsd"].get("plugin_dir", None)
    if plugin_dir:
        LOG.info("Trying to load custom plugins from '{}'".format(plugin_dir))
        cpm = PluginManager(config)
        plugins_list = cpm.load_plugins(plugin_dir)
        LOG.info("Discovered {} modules to load".format(len(plugins_list)))
        for o in plugins_list:
            plugin_obj = None
            if enabled_plugins:
                if o["name"] in enabled_plugins:
                    plugin_obj = o["obj"]
                else:
                    LOG.info(
                        "'{}' plugin not listed in config aprsd:enabled_plugins".format(
                            o["name"]
                        )
                    )
            else:
                # not setting enabled plugins means load all?
                plugin_obj = o["obj"]

            if plugin_obj:
                LOG.info(
                    "Registering Command plugin '{}'({}) '{}'".format(
                        o["name"], o["obj"].version, o["obj"].command_regex
                    )
                )
                pm.register(o["obj"])

    else:
        LOG.info("Skipping Custom Plugins.")

    LOG.info("Completed Plugin Loading.")
    return pm


class PluginManager(object):
    def __init__(self, config):
        self.obj_list = []
        self.config = config

    def load_plugins(self, module_path):
        dir_path = os.path.dirname(os.path.realpath(module_path))
        pattern = "*.py"

        self.obj_list = []

        for path, subdirs, files in os.walk(dir_path):
            for name in files:
                if fnmatch.fnmatch(name, pattern):
                    found_module = imp.find_module(name[:-3], [path])
                    module = imp.load_module(
                        name, found_module[0], found_module[1], found_module[2]
                    )
                    for mem_name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and inspect.getmodule(obj) is module
                            and self.is_plugin(obj)
                        ):
                            self.obj_list.append(
                                {"name": mem_name, "obj": obj(self.config)}
                            )

        return self.obj_list

    def is_plugin(self, obj):
        for c in inspect.getmro(obj):
            if issubclass(c, APRSDPluginBase):
                return True

        return False


class APRSDCommandSpec:
    """A hook specification namespace."""

    @hookspec
    def run(self, fromcall, message, ack):
        """My special little hook that you can customize."""
        pass


@six.add_metaclass(abc.ABCMeta)
class APRSDPluginBase(object):
    def __init__(self, config):
        """The aprsd config object is stored."""
        self.config = config

    @property
    def command_name(self):
        """The usage string help."""
        raise NotImplementedError

    @property
    def command_regex(self):
        """The regex to match from the caller"""
        raise NotImplementedError

    @property
    def version(self):
        """Version"""
        raise NotImplementedError

    @hookimpl
    def run(self, fromcall, message, ack):
        if re.search(self.command_regex, message):
            return self.command(fromcall, message, ack)

    @abc.abstractmethod
    def command(self, fromcall, message, ack):
        """This is the command that runs when the regex matches.

        To reply with a message over the air, return a string
        to send.
        """
        pass


class FortunePlugin(APRSDPluginBase):
    """Fortune."""

    version = "1.0"
    command_regex = "^[fF]"
    command_name = "fortune"

    def command(self, fromcall, message, ack):
        LOG.info("FortunePlugin")
        reply = None
        try:
            process = subprocess.Popen(
                ["/usr/games/fortune", "-s", "-n 60"], stdout=subprocess.PIPE
            )
            reply = process.communicate()[0]
            # send_message(fromcall, reply.rstrip())
            reply = reply.decode(errors="ignore").rstrip()
        except Exception as ex:
            reply = "Fortune command failed '{}'".format(ex)
            LOG.error(reply)

        return reply


class LocationPlugin(APRSDPluginBase):
    """Location!"""

    version = "1.0"
    command_regex = "^[lL]"
    command_name = "location"

    def command(self, fromcall, message, ack):
        LOG.info("Location Plugin")
        # get last location of a callsign, get descriptive name from weather service
        try:
            a = re.search(
                r"^.*\s+(.*)", message
            )  # optional second argument is a callsign to search
            if a is not None:
                searchcall = a.group(1)
                searchcall = searchcall.upper()
            else:
                searchcall = (
                    fromcall  # if no second argument, search for calling station
                )
            url = (
                "http://api.aprs.fi/api/get?name="
                + searchcall
                + "&what=loc&apikey=104070.f9lE8qg34L8MZF&format=json"
            )
            response = requests.get(url)
            # aprs_data = json.loads(response.read())
            aprs_data = json.loads(response.text)
            lat = aprs_data["entries"][0]["lat"]
            lon = aprs_data["entries"][0]["lng"]
            try:  # altitude not always provided
                alt = aprs_data["entries"][0]["altitude"]
            except Exception:
                alt = 0
            altfeet = int(alt * 3.28084)
            aprs_lasttime_seconds = aprs_data["entries"][0]["lasttime"]
            aprs_lasttime_seconds = aprs_lasttime_seconds.encode(
                "ascii", errors="ignore"
            )  # unicode to ascii
            delta_seconds = time.time() - int(aprs_lasttime_seconds)
            delta_hours = delta_seconds / 60 / 60
            url2 = (
                "https://forecast.weather.gov/MapClick.php?lat="
                + str(lat)
                + "&lon="
                + str(lon)
                + "&FcstType=json"
            )
            response2 = requests.get(url2)
            wx_data = json.loads(response2.text)

            reply = "{}: {} {}' {},{} {}h ago".format(
                searchcall,
                wx_data["location"]["areaDescription"],
                str(altfeet),
                str(alt),
                str(lon),
                str("%.1f" % round(delta_hours, 1)),
            ).rstrip()
        except Exception as e:
            LOG.debug("Locate failed with:  " + "%s" % str(e))
            reply = "Unable to find station " + searchcall + ".  Sending beacons?"

        return reply


class PingPlugin(APRSDPluginBase):
    """Ping."""

    version = "1.0"
    command_regex = "^[pP]"
    command_name = "ping"

    def command(self, fromcall, message, ack):
        LOG.info("PINGPlugin")
        stm = time.localtime()
        h = stm.tm_hour
        m = stm.tm_min
        s = stm.tm_sec
        reply = (
            "Pong! " + str(h).zfill(2) + ":" + str(m).zfill(2) + ":" + str(s).zfill(2)
        )
        return reply.rstrip()


class TimePlugin(APRSDPluginBase):
    """Time command."""

    version = "1.0"
    command_regex = "^[tT]"
    command_name = "time"

    def command(self, fromcall, message, ack):
        LOG.info("TIME COMMAND")
        stm = time.localtime()
        h = stm.tm_hour
        m = stm.tm_min
        cur_time = fuzzy(h, m, 1)
        reply = "{} ({}:{} PDT) ({})".format(
            cur_time, str(h), str(m).rjust(2, "0"), message.rstrip()
        )
        return reply


class WeatherPlugin(APRSDPluginBase):
    """Weather Command"""

    version = "1.0"
    command_regex = "^[wW]"
    command_name = "weather"

    def command(self, fromcall, message, ack):
        LOG.info("Weather Plugin")
        try:
            url = (
                "http://api.aprs.fi/api/get?"
                "&what=loc&apikey=104070.f9lE8qg34L8MZF&format=json"
                "&name=%s" % fromcall
            )
            response = requests.get(url)
            # aprs_data = json.loads(response.read())
            aprs_data = json.loads(response.text)
            lat = aprs_data["entries"][0]["lat"]
            lon = aprs_data["entries"][0]["lng"]
            url2 = (
                "https://forecast.weather.gov/MapClick.php?lat=%s"
                "&lon=%s&FcstType=json" % (lat, lon)
            )
            response2 = requests.get(url2)
            # wx_data = json.loads(response2.read())
            wx_data = json.loads(response2.text)
            reply = (
                "%sF(%sF/%sF) %s. %s, %s."
                % (
                    wx_data["currentobservation"]["Temp"],
                    wx_data["data"]["temperature"][0],
                    wx_data["data"]["temperature"][1],
                    wx_data["data"]["weather"][0],
                    wx_data["time"]["startPeriodName"][1],
                    wx_data["data"]["weather"][1],
                ).rstrip()
            )
            LOG.debug("reply: '{}' ".format(reply))
        except Exception as e:
            LOG.debug("Weather failed with:  " + "%s" % str(e))
            reply = "Unable to find you (send beacon?)"

        return reply
