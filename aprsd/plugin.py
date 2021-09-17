# The base plugin class
import abc
import fnmatch
import importlib
import inspect
import logging
import os
import re
import threading

import pluggy
from thesmuggler import smuggle

from aprsd import client, messaging, packets, threads


# setup the global logger
LOG = logging.getLogger("APRSD")

hookspec = pluggy.HookspecMarker("aprsd")
hookimpl = pluggy.HookimplMarker("aprsd")

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


class APRSDCommandSpec:
    """A hook specification namespace."""

    @hookspec
    def filter(self, packet):
        """My special little hook that you can customize."""


class APRSDPluginBase(metaclass=abc.ABCMeta):
    """The base class for all APRSD Plugins."""

    config = None
    rx_count = 0
    tx_count = 0
    version = "1.0"

    # Holds the list of APRSDThreads that the plugin creates
    threads = []
    # Set this in setup()
    enabled = False

    def __init__(self, config):
        self.config = config
        self.message_counter = 0
        self.setup()
        threads = self.create_threads()
        if threads:
            self.threads = threads
        if self.threads:
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

    @property
    def version(self):
        """Version"""
        raise NotImplementedError

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

    @hookimpl
    @abc.abstractmethod
    def filter(self, packet):
        pass

    @abc.abstractmethod
    def process(self, packet):
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
        if "watch_list" in self.config["aprsd"] and self.config["aprsd"][
            "watch_list"
        ].get("enabled", False):
            # watch list is enabled
            self.enabled = True
            watch_list = self.config["aprsd"]["watch_list"].get(
                "callsigns",
                [],
            )
            # make sure the timeout is set or this doesn't work
            if watch_list:
                aprs_client = client.factory.create().client
                filter_str = "b/{}".format("/".join(watch_list))
                aprs_client.set_filter(filter_str)
            else:
                LOG.warning("Watch list enabled, but no callsigns set.")

    def filter(self, packet):
        if self.enabled:
            wl = packets.WatchList()
            result = messaging.NULL_MESSAGE
            if wl.callsign_in_watchlist(packet["from"]):
                # packet is from a callsign in the watch list
                self.rx_inc()
                result = self.process()
                if result:
                    self.tx_inc()
                wl.update_seen(packet)
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

    def setup(self):
        """Do any plugin setup here."""
        self.enabled = True

    @hookimpl
    def filter(self, packet):
        result = None

        message = packet.get("message_text", None)
        msg_format = packet.get("format", None)
        tocall = packet.get("addresse", None)

        # Only process messages destined for us
        # and is an APRS message format and has a message.
        if (
            tocall == self.config["aprs"]["login"]
            and msg_format == "message"
            and message
        ):
            if re.search(self.command_regex, message):
                self.rx_inc()
                if self.enabled:
                    result = self.process(packet)
                    if result:
                        self.tx_inc()
                else:
                    LOG.warning(f"{self.__class__} isn't enabled.")

        return result


class PluginManager:
    # The singleton instance object for this class
    _instance = None

    # the pluggy PluginManager for all Message plugins
    _pluggy_pm = None

    # aprsd config dict
    config = None

    lock = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any initialization here.
            cls._instance.lock = threading.Lock()
        return cls._instance

    def __init__(self, config=None):
        self.obj_list = []
        if config:
            self.config = config

    def load_plugins_from_path(self, module_path):
        if not os.path.exists(module_path):
            LOG.error(f"plugin path '{module_path}' doesn't exist.")
            return None

        dir_path = os.path.realpath(module_path)
        pattern = "*.py"

        self.obj_list = []

        for path, _subdirs, files in os.walk(dir_path):
            for name in files:
                if fnmatch.fnmatch(name, pattern):
                    LOG.debug(f"MODULE? '{name}' '{path}'")
                    module = smuggle(f"{path}/{name}")
                    for mem_name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and self.is_plugin(obj):
                            self.obj_list.append(
                                {"name": mem_name, "obj": obj(self.config)},
                            )

        return self.obj_list

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
        module_name, class_name = module_class_string.rsplit(".", 1)
        try:
            module = importlib.import_module(module_name)
            module = importlib.reload(module)
        except Exception as ex:
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
                config=self.config,
            )
            if plugin_obj:
                LOG.info(
                    "Registering plugin '{}'({})".format(
                        plugin_name,
                        plugin_obj.version,
                    ),
                )
                self._pluggy_pm.register(plugin_obj)
        except Exception as ex:
            LOG.exception(f"Couldn't load plugin '{plugin_name}'", ex)

    def reload_plugins(self):
        with self.lock:
            del self._pluggy_pm
            self.setup_plugins()

    def setup_plugins(self):
        """Create the plugin manager and register plugins."""

        LOG.info("Loading APRSD Plugins")
        enabled_plugins = self.config["aprsd"].get("enabled_plugins", None)
        self._pluggy_pm = pluggy.PluginManager("aprsd")
        self._pluggy_pm.add_hookspecs(APRSDCommandSpec)
        if enabled_plugins:
            for p_name in enabled_plugins:
                self._load_plugin(p_name)
        else:
            # Enabled plugins isn't set, so we default to loading all of
            # the core plugins.
            for p_name in CORE_MESSAGE_PLUGINS:
                self._load_plugin(p_name)

        if self.config["aprsd"]["watch_list"].get("enabled", False):
            LOG.info("Loading APRSD WatchList Plugins")
            enabled_notify_plugins = self.config["aprsd"]["watch_list"].get(
                "enabled_plugins",
                None,
            )
            if enabled_notify_plugins:
                for p_name in enabled_notify_plugins:
                    self._load_plugin(p_name)
        LOG.info("Completed Plugin Loading.")

    def run(self, packet):
        """Execute all the pluguns run method."""
        with self.lock:
            return self._pluggy_pm.hook.filter(packet=packet)

    def register_msg(self, obj):
        """Register the plugin."""
        self._pluggy_pm.register(obj)

    def get_plugins(self):
        return self._pluggy_pm.get_plugins()
