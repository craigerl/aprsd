# The base plugin class
import abc
import fnmatch
import importlib
import inspect
import json
import logging
import os
import re
import shutil
import subprocess
import time

import pluggy
import requests
import six
from thesmuggler import smuggle

import aprsd
from aprsd import email, messaging
from aprsd.fuzzyclock import fuzzy

# setup the global logger
LOG = logging.getLogger("APRSD")

hookspec = pluggy.HookspecMarker("aprsd")
hookimpl = pluggy.HookimplMarker("aprsd")

CORE_PLUGINS = [
    "aprsd.plugin.EmailPlugin",
    "aprsd.plugin.FortunePlugin",
    "aprsd.plugin.LocationPlugin",
    "aprsd.plugin.PingPlugin",
    "aprsd.plugin.QueryPlugin",
    "aprsd.plugin.TimePlugin",
    "aprsd.plugin.WeatherPlugin",
    "aprsd.plugin.VersionPlugin",
]


class PluginManager(object):
    # The singleton instance object for this class
    _instance = None

    # the pluggy PluginManager
    _pluggy_pm = None

    # aprsd config dict
    config = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self, config=None):
        self.obj_list = []
        if config:
            self.config = config

    def load_plugins_from_path(self, module_path):
        if not os.path.exists(module_path):
            LOG.error("plugin path '{}' doesn't exist.".format(module_path))
            return None

        dir_path = os.path.realpath(module_path)
        pattern = "*.py"

        self.obj_list = []

        for path, _subdirs, files in os.walk(dir_path):
            for name in files:
                if fnmatch.fnmatch(name, pattern):
                    LOG.debug("MODULE? '{}' '{}'".format(name, path))
                    module = smuggle("{}/{}".format(path, name))
                    for mem_name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and self.is_plugin(obj):
                            self.obj_list.append(
                                {"name": mem_name, "obj": obj(self.config)}
                            )

        return self.obj_list

    def is_plugin(self, obj):
        for c in inspect.getmro(obj):
            if issubclass(c, APRSDPluginBase):
                return True

        return False

    def _create_class(self, module_class_string, super_cls: type = None, **kwargs):
        """
        Method to create a class from a fqn python string.

        :param module_class_string: full name of the class to create an object of
        :param super_cls: expected super class for validity, None if bypass
        :param kwargs: parameters to pass
        :return:
        """
        module_name, class_name = module_class_string.rsplit(".", 1)
        try:
            module = importlib.import_module(module_name)
        except Exception as ex:
            LOG.error("Failed to load Plugin '{}' : '{}'".format(module_name, ex))
            return

        assert hasattr(module, class_name), "class {} is not in {}".format(
            class_name, module_name
        )
        # click.echo('reading class {} from module {}'.format(
        #     class_name, module_name))
        cls = getattr(module, class_name)
        if super_cls is not None:
            assert issubclass(cls, super_cls), "class {} should inherit from {}".format(
                class_name, super_cls.__name__
            )
        # click.echo('initialising {} with params {}'.format(class_name, kwargs))
        obj = cls(**kwargs)
        return obj

    def _load_plugin(self, plugin_name):
        """

        Given a python fully qualified class path.name,
        Try importing the path, then creating the object,
        then registering it as a aprsd Command Plugin
        """
        plugin_obj = None
        try:
            plugin_obj = self._create_class(
                plugin_name, APRSDPluginBase, config=self.config
            )
            if plugin_obj:
                LOG.info(
                    "Registering Command plugin '{}'({})  '{}'".format(
                        plugin_name, plugin_obj.version, plugin_obj.command_regex
                    )
                )
                self._pluggy_pm.register(plugin_obj)
        except Exception as ex:
            LOG.exception("Couldn't load plugin '{}'".format(plugin_name), ex)

    def setup_plugins(self):
        """Create the plugin manager and register plugins."""

        LOG.info("Loading Core APRSD Command Plugins")
        enabled_plugins = self.config["aprsd"].get("enabled_plugins", None)
        self._pluggy_pm = pluggy.PluginManager("aprsd")
        self._pluggy_pm.add_hookspecs(APRSDCommandSpec)
        if enabled_plugins:
            for p_name in enabled_plugins:
                self._load_plugin(p_name)
        else:
            # Enabled plugins isn't set, so we default to loading all of
            # the core plugins.
            for p_name in CORE_PLUGINS:
                self._load_plugin(p_name)

        plugin_dir = self.config["aprsd"].get("plugin_dir", None)
        if plugin_dir:
            LOG.info("Trying to load custom plugins from '{}'".format(plugin_dir))
            plugins_list = self.load_plugins_from_path(plugin_dir)
            if plugins_list:
                LOG.info("Discovered {} modules to load".format(len(plugins_list)))
                for o in plugins_list:
                    plugin_obj = None
                    # not setting enabled plugins means load all?
                    plugin_obj = o["obj"]

                    if plugin_obj:
                        LOG.info(
                            "Registering Command plugin '{}'({}) '{}'".format(
                                o["name"], o["obj"].version, o["obj"].command_regex
                            )
                        )
                        self._pluggy_pm.register(o["obj"])

        else:
            LOG.info("Skipping Custom Plugins directory.")
        LOG.info("Completed Plugin Loading.")

    def run(self, *args, **kwargs):
        """Execute all the pluguns run method."""
        return self._pluggy_pm.hook.run(*args, **kwargs)

    def register(self, obj):
        """Register the plugin."""
        self._pluggy_pm.register(obj)

    def get_plugins(self):
        return self._pluggy_pm.get_plugins()


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

        fortune_path = shutil.which("fortune")
        if not fortune_path:
            reply = "Fortune command not installed"
            return reply

        try:
            process = subprocess.Popen(
                [fortune_path, "-s", "-n 60"], stdout=subprocess.PIPE
            )
            reply = process.communicate()[0]
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

    config_items = {"apikey": "aprs.fi api key here"}

    def command(self, fromcall, message, ack):
        LOG.info("Location Plugin")
        # get last location of a callsign, get descriptive name from weather service
        try:
            # optional second argument is a callsign to search
            a = re.search(r"^.*\s+(.*)", message)
            if a is not None:
                searchcall = a.group(1)
                searchcall = searchcall.upper()
            else:
                # if no second argument, search for calling station
                searchcall = fromcall
            url = (
                "http://api.aprs.fi/api/get?name="
                + searchcall
                + "&what=loc&apikey=104070.f9lE8qg34L8MZF&format=json"
            )
            response = requests.get(url)
            # aprs_data = json.loads(response.read())
            aprs_data = json.loads(response.text)
            LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
            lat = aprs_data["entries"][0]["lat"]
            lon = aprs_data["entries"][0]["lng"]
            try:  # altitude not always provided
                alt = aprs_data["entries"][0]["altitude"]
            except Exception:
                alt = 0
            altfeet = int(alt * 3.28084)
            aprs_lasttime_seconds = aprs_data["entries"][0]["lasttime"]
            # aprs_lasttime_seconds = aprs_lasttime_seconds.encode(
            #    "ascii", errors="ignore"
            # )  # unicode to ascii
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


class QueryPlugin(APRSDPluginBase):
    """Query command."""

    version = "1.0"
    command_regex = r"^\?.*"
    command_name = "query"

    def command(self, fromcall, message, ack):
        LOG.info("Query COMMAND")

        tracker = messaging.MsgTrack()
        reply = "Pending Messages ({})".format(len(tracker))

        searchstring = "^" + self.config["ham"]["callsign"] + ".*"
        # only I can do admin commands
        if re.search(searchstring, fromcall):
            r = re.search(r"^\?-\*", message)
            if r is not None:
                if len(tracker) > 0:
                    reply = "Resend ALL Delayed msgs"
                    LOG.debug(reply)
                    tracker.restart_delayed()
                else:
                    reply = "No Delayed Msgs"
                    LOG.debug(reply)
                return reply

            r = re.search(r"^\?-[fF]!", message)
            if r is not None:
                reply = "Deleting ALL Delayed msgs."
                LOG.debug(reply)
                tracker.flush()
                return reply

        return reply


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
                )
            ).rstrip()
            LOG.debug("reply: '{}' ".format(reply))
        except Exception as e:
            LOG.debug("Weather failed with:  " + "%s" % str(e))
            reply = "Unable to find you (send beacon?)"

        return reply


class EmailPlugin(APRSDPluginBase):
    """Email Plugin."""

    version = "1.0"
    command_regex = "^-.*"
    command_name = "email"

    # message_number:time combos so we don't resend the same email in
    # five mins {int:int}
    email_sent_dict = {}

    def command(self, fromcall, message, ack):
        LOG.info("Email COMMAND")
        reply = None

        searchstring = "^" + self.config["ham"]["callsign"] + ".*"
        # only I can do email
        if re.search(searchstring, fromcall):
            # digits only, first one is number of emails to resend
            r = re.search("^-([0-9])[0-9]*$", message)
            if r is not None:
                LOG.debug("RESEND EMAIL")
                email.resend_email(r.group(1), fromcall)
                reply = messaging.NULL_MESSAGE
            # -user@address.com body of email
            elif re.search(r"^-([A-Za-z0-9_\-\.@]+) (.*)", message):
                # (same search again)
                a = re.search(r"^-([A-Za-z0-9_\-\.@]+) (.*)", message)
                if a is not None:
                    to_addr = a.group(1)
                    content = a.group(2)

                    email_address = email.get_email_from_shortcut(to_addr)
                    if not email_address:
                        reply = "Bad email address"
                        return reply

                    # send recipient link to aprs.fi map
                    mapme = False
                    if content == "mapme":
                        mapme = True
                        content = "Click for my location: http://aprs.fi/{}".format(
                            self.config["ham"]["callsign"]
                        )
                    too_soon = 0
                    now = time.time()
                    # see if we sent this msg number recently
                    if ack in self.email_sent_dict:
                        # BUG(hemna) - when we get a 2 different email command
                        # with the same ack #, we don't send it.
                        timedelta = now - self.email_sent_dict[ack]
                        if timedelta < 300:  # five minutes
                            too_soon = 1
                    if not too_soon or ack == 0:
                        LOG.info("Send email '{}'".format(content))
                        send_result = email.send_email(to_addr, content)
                        if send_result != 0:
                            reply = "-{} failed".format(to_addr)
                            # messaging.send_message(fromcall, "-" + to_addr + " failed")
                        else:
                            # clear email sent dictionary if somehow goes over 100
                            if len(self.email_sent_dict) > 98:
                                LOG.debug(
                                    "DEBUG: email_sent_dict is big ("
                                    + str(len(self.email_sent_dict))
                                    + ") clearing out."
                                )
                                self.email_sent_dict.clear()
                            self.email_sent_dict[ack] = now
                            #don't really need a response, ack is enough
                            #if mapme:
                            #    reply = "mapme email sent"
                            #else:
                            #    reply = "Email sent."
                    else:
                        LOG.info(
                            "Email for message number "
                            + ack
                            + " recently sent, not sending again."
                        )
            else:
                reply = "Bad email address"
                # messaging.send_message(fromcall, "Bad email address")

        return reply


class VersionPlugin(APRSDPluginBase):
    """Version of APRSD Plugin."""

    version = "1.0"
    command_regex = "^[vV]"
    command_name = "version"

    # message_number:time combos so we don't resend the same email in
    # five mins {int:int}
    email_sent_dict = {}

    def command(self, fromcall, message, ack):
        LOG.info("Version COMMAND")
        return "APRSD version '{}'".format(aprsd.__version__)
