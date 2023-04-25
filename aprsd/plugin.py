# The base plugin class
import abc
import importlib
import inspect
import logging
import re
import textwrap
import threading

from oslo_config import cfg
import pluggy

import aprsd
from aprsd import client, packets, threads
from aprsd.packets import watch_list


# setup the global logger
CONF = cfg.CONF
LOG = logging.getLogger("APRSD")

CORE_MESSAGE_PLUGINS = [
    "aprsd.plugins.email.EmailPlugin",
    "aprsd.plugins.fortune.FortunePlugin",
    "aprsd.plugins.location.LocationPlugin",
    "aprsd.plugins.ping.PingPlugin",
    "aprsd.plugins.query.QueryPlugin",
    "aprsd.plugins.time.TimePlugin",
    "aprsd.plugins.weather.USWeatherPlugin",
    "aprsd.plugins.version.VersionPlugin",
]

CORE_NOTIFY_PLUGINS = [
    "aprsd.plugins.notify.NotifySeenPlugin",
]

hookspec = pluggy.HookspecMarker("aprsd")
hookimpl = pluggy.HookimplMarker("aprsd")


class APRSDPluginSpec:
    """A hook specification namespace."""

    @hookspec
    def filter(self, packet: packets.core.Packet):
        """My special little hook that you can customize."""


class APRSDPluginBase(metaclass=abc.ABCMeta):
    """The base class for all APRSD Plugins."""

    config = None
    rx_count = 0
    tx_count = 0
    version = aprsd.__version__

    # Holds the list of APRSDThreads that the plugin creates
    threads = []
    # Set this in setup()
    enabled = False

    def __init__(self):
        self.message_counter = 0
        self.setup()
        self.threads = self.create_threads() or []
        self.start_threads()

    def start_threads(self):
        if self.enabled and self.threads:
            if not isinstance(self.threads, list):
                self.threads = [self.threads]

            try:
                for thread in self.threads:
                    if isinstance(thread, threads.APRSDThread):
                        thread.start()
                    else:
                        LOG.error(
                            "Can't start thread {}:{}, Must be a child "
                            "of aprsd.threads.APRSDThread".format(
                                self,
                                thread,
                            ),
                        )
            except Exception:
                LOG.error(
                    "Failed to start threads for plugin {}".format(
                        self,
                    ),
                )

    @property
    def message_count(self):
        return self.message_counter

    def help(self):
        return "Help!"

    @abc.abstractmethod
    def setup(self):
        """Do any plugin setup here."""
        self.enabled = True

    def create_threads(self):
        """Gives the plugin writer the ability start a background thread."""
        return []

    def rx_inc(self):
        self.rx_count += 1

    def tx_inc(self):
        self.tx_count += 1

    def stop_threads(self):
        """Stop any threads this plugin might have created."""
        for thread in self.threads:
            if isinstance(thread, threads.APRSDThread):
                thread.stop()

    @abc.abstractmethod
    def filter(self, packet: packets.core.Packet):
        pass

    @abc.abstractmethod
    def process(self, packet: packets.core.Packet):
        """This is called when the filter passes."""


class APRSDWatchListPluginBase(APRSDPluginBase, metaclass=abc.ABCMeta):
    """Base plugin class for all notification APRSD plugins.

    All these plugins will get every packet seen by APRSD's
    registered list of HAM callsigns in the config file's
    watch_list.

    When you want to 'notify' something when a packet is seen
    by a particular HAM callsign, write a plugin based off of
    this class.
    """

    def setup(self):
        # if we have a watch list enabled, we need to add filtering
        # to enable seeing packets from the watch list.
        if CONF.watch_list.enabled:
            # watch list is enabled
            self.enabled = True
            watch_list = CONF.watch_list.callsigns
            # make sure the timeout is set or this doesn't work
            if watch_list:
                aprs_client = client.factory.create().client
                filter_str = "b/{}".format("/".join(watch_list))
                aprs_client.set_filter(filter_str)
            else:
                LOG.warning("Watch list enabled, but no callsigns set.")

    @hookimpl
    def filter(self, packet: packets.core.Packet):
        result = packets.NULL_MESSAGE
        if self.enabled:
            wl = watch_list.WatchList()
            if wl.callsign_in_watchlist(packet.from_call):
                # packet is from a callsign in the watch list
                self.rx_inc()
                try:
                    result = self.process(packet)
                except Exception as ex:
                    LOG.error(
                        "Plugin {} failed to process packet {}".format(
                            self.__class__, ex,
                        ),
                    )
                if result:
                    self.tx_inc()
        else:
            LOG.warning(f"{self.__class__} plugin is not enabled")

        return result


class APRSDRegexCommandPluginBase(APRSDPluginBase, metaclass=abc.ABCMeta):
    """Base Message plugin class.

    When you want to search for a particular command in an
    APRSD message and send a direct reply, write a plugin
    based off of this class.
    """

    @property
    def command_name(self):
        """The usage string help."""
        raise NotImplementedError

    @property
    def command_regex(self):
        """The regex to match from the caller"""
        raise NotImplementedError

    def help(self):
        return "{}: {}".format(
            self.command_name.lower(),
            self.command_regex,
        )

    def setup(self):
        """Do any plugin setup here."""
        self.enabled = True

    @hookimpl
    def filter(self, packet: packets.core.MessagePacket):
        LOG.info(f"{self.__class__.__name__} called")
        if not self.enabled:
            result = f"{self.__class__.__name__} isn't enabled"
            LOG.warning(result)
            return result

        if not isinstance(packet, packets.core.MessagePacket):
            LOG.warning(f"{self.__class__.__name__} Got a {packet.__class__.__name__} ignoring")
            return packets.NULL_MESSAGE

        result = None

        message = packet.message_text
        tocall = packet.to_call

        # Only process messages destined for us
        # and is an APRS message format and has a message.
        if (
            tocall == CONF.callsign
            and isinstance(packet, packets.core.MessagePacket)
            and message
        ):
            if re.search(self.command_regex, message, re.IGNORECASE):
                self.rx_inc()
                try:
                    result = self.process(packet)
                except Exception as ex:
                    LOG.error(
                        "Plugin {} failed to process packet {}".format(
                            self.__class__, ex,
                        ),
                    )
                    LOG.exception(ex)
                if result:
                    self.tx_inc()

        return result


class APRSFIKEYMixin:
    """Mixin class to enable checking the existence of the aprs.fi apiKey."""

    def ensure_aprs_fi_key(self):
        if not CONF.aprs_fi.apiKey:
            LOG.error("Config aprs_fi.apiKey is not set")
            self.enabled = False
        else:
            self.enabled = True


class HelpPlugin(APRSDRegexCommandPluginBase):
    """Help Plugin that is always enabled.

    This plugin is in this file to prevent a circular import.
    """

    command_regex = "^[hH]"
    command_name = "help"

    def help(self):
        return "Help: send APRS help or help <plugin>"

    def process(self, packet: packets.core.MessagePacket):
        LOG.info("HelpPlugin")
        # fromcall = packet.get("from")
        message = packet.message_text
        # ack = packet.get("msgNo", "0")
        a = re.search(r"^.*\s+(.*)", message)
        command_name = None
        if a is not None:
            command_name = a.group(1).lower()

        pm = PluginManager()

        if command_name and "?" not in command_name:
            # user wants help for a specific plugin
            reply = None
            for p in pm.get_plugins():
                if (
                    p.enabled and isinstance(p, APRSDRegexCommandPluginBase)
                    and p.command_name.lower() == command_name
                ):
                    reply = p.help()

            if reply:
                return reply

        list = []
        for p in pm.get_plugins():
            LOG.debug(p)
            if p.enabled and isinstance(p, APRSDRegexCommandPluginBase):
                name = p.command_name.lower()
                if name not in list and "help" not in name:
                    list.append(name)

        list.sort()
        reply = " ".join(list)
        lines = textwrap.wrap(reply, 60)
        replies = ["Send APRS MSG of 'help' or 'help <plugin>'"]
        for line in lines:
            replies.append(f"plugins: {line}")

        for entry in replies:
            LOG.debug(f"{len(entry)} {entry}")

        LOG.debug(f"{replies}")
        return replies


class PluginManager:
    # The singleton instance object for this class
    _instance = None

    # the pluggy PluginManager for all Message plugins
    _pluggy_pm = None
    # the pluggy PluginManager for all WatchList plugins
    _watchlist_pm = None

    lock = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any initialization here.
            cls._instance.lock = threading.Lock()
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._pluggy_pm = pluggy.PluginManager("aprsd")
        self._pluggy_pm.add_hookspecs(APRSDPluginSpec)
        # For the watchlist plugins
        self._watchlist_pm = pluggy.PluginManager("aprsd")
        self._watchlist_pm.add_hookspecs(APRSDPluginSpec)

    def is_plugin(self, obj):
        for c in inspect.getmro(obj):
            if issubclass(c, APRSDPluginBase):
                return True

        return False

    def _create_class(
        self,
        module_class_string,
        super_cls: type = None,
        **kwargs,
    ):
        """
        Method to create a class from a fqn python string.
        :param module_class_string: full name of the class to create an object
        :param super_cls: expected super class for validity, None if bypass
        :param kwargs: parameters to pass
        :return:
        """
        module_name = None
        class_name = None
        try:
            module_name, class_name = module_class_string.rsplit(".", 1)
            module = importlib.import_module(module_name)
            module = importlib.reload(module)
        except Exception as ex:
            if not module_name:
                LOG.error(f"Failed to load Plugin {module_class_string}")
            else:
                LOG.error(f"Failed to load Plugin '{module_name}' : '{ex}'")
            return

        assert hasattr(module, class_name), "class {} is not in {}".format(
            class_name,
            module_name,
        )
        # click.echo('reading class {} from module {}'.format(
        #     class_name, module_name))
        cls = getattr(module, class_name)
        if super_cls is not None:
            assert issubclass(cls, super_cls), "class {} should inherit from {}".format(
                class_name,
                super_cls.__name__,
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
                plugin_name,
                APRSDPluginBase,
            )
            if plugin_obj:
                if isinstance(plugin_obj, APRSDWatchListPluginBase):
                    if plugin_obj.enabled:
                        LOG.info(
                            "Registering WatchList plugin '{}'({})".format(
                                plugin_name,
                                plugin_obj.version,
                            ),
                        )
                        self._watchlist_pm.register(plugin_obj)
                    else:
                        LOG.warning(f"Plugin {plugin_obj.__class__.__name__} is disabled")
                elif isinstance(plugin_obj, APRSDRegexCommandPluginBase):
                    if plugin_obj.enabled:
                        LOG.info(
                            "Registering Regex plugin '{}'({}) -- {}".format(
                                plugin_name,
                                plugin_obj.version,
                                plugin_obj.command_regex,
                            ),
                        )
                        self._pluggy_pm.register(plugin_obj)
                    else:
                        LOG.warning(f"Plugin {plugin_obj.__class__.__name__} is disabled")
                elif isinstance(plugin_obj, APRSDPluginBase):
                    if plugin_obj.enabled:
                        LOG.info(
                            "Registering Base plugin '{}'({})".format(
                                plugin_name,
                                plugin_obj.version,
                            ),
                        )
                        self._pluggy_pm.register(plugin_obj)
                    else:
                        LOG.warning(f"Plugin {plugin_obj.__class__.__name__} is disabled")
        except Exception as ex:
            LOG.error(f"Couldn't load plugin '{plugin_name}'")
            LOG.exception(ex)

    def reload_plugins(self):
        with self.lock:
            del self._pluggy_pm
            self.setup_plugins()

    def setup_plugins(self, load_help_plugin=True):
        """Create the plugin manager and register plugins."""

        LOG.info("Loading APRSD Plugins")
        # Help plugin is always enabled.
        if load_help_plugin:
            _help = HelpPlugin()
            self._pluggy_pm.register(_help)

        enabled_plugins = CONF.enabled_plugins
        if enabled_plugins:
            for p_name in enabled_plugins:
                self._load_plugin(p_name)
        else:
            # Enabled plugins isn't set, so we default to loading all of
            # the core plugins.
            for p_name in CORE_MESSAGE_PLUGINS:
                self._load_plugin(p_name)

        LOG.info("Completed Plugin Loading.")

    def run(self, packet: packets.core.MessagePacket):
        """Execute all the plugins run method."""
        with self.lock:
            return self._pluggy_pm.hook.filter(packet=packet)

    def run_watchlist(self, packet: packets.core.Packet):
        with self.lock:
            return self._watchlist_pm.hook.filter(packet=packet)

    def stop(self):
        """Stop all threads created by all plugins."""
        with self.lock:
            for p in self.get_plugins():
                if hasattr(p, "stop_threads"):
                    p.stop_threads()

    def register_msg(self, obj):
        """Register the plugin."""
        with self.lock:
            self._pluggy_pm.register(obj)

    def get_plugins(self):
        plugin_list = []
        if self._pluggy_pm:
            for plug in self._pluggy_pm.get_plugins():
                plugin_list.append(plug)
        if self._watchlist_pm:
            for plug in self._watchlist_pm.get_plugins():
                plugin_list.append(plug)

        return plugin_list

    def get_watchlist_plugins(self):
        pl = []
        if self._watchlist_pm:
            for plug in self._watchlist_pm.get_plugins():
                pl.append(plug)
        return pl

    def get_message_plugins(self):
        pl = []
        if self._pluggy_pm:
            for plug in self._pluggy_pm.get_plugins():
                pl.append(plug)
        return pl
