# The base plugin class
import abc
import fnmatch
import importlib
import inspect
import logging
import os
import re
import threading

from aprsd import messaging, packets
import pluggy
from thesmuggler import smuggle


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
    message_counter = 0
    version = "1.0"

    def __init__(self, config):
        self.config = config
        self.message_counter = 0
        self.setup()

    @property
    def message_count(self):
        return self.message_counter

    @property
    def version(self):
        """Version"""
        raise NotImplementedError

    def setup(self):
        """Do any plugin setup here."""
        pass

    @hookimpl
    @abc.abstractmethod
    def filter(self, packet):
        pass

    @abc.abstractmethod
    def process(self, packet):
        """This is called when the filter passes."""
        pass


class APRSDWatchListPluginBase(APRSDPluginBase, metaclass=abc.ABCMeta):
    """Base plugin class for all notification APRSD plugins.

    All these plugins will get every packet seen by APRSD's
    registered list of HAM callsigns in the config file's
    watch_list.

    When you want to 'notify' something when a packet is seen
    by a particular HAM callsign, write a plugin based off of
    this class.
    """

    def filter(self, packet):
        wl = packets.WatchList()
        result = messaging.NULL_MESSAGE
        if wl.callsign_in_watchlist(packet["from"]):
            # packet is from a callsign in the watch list
            result = self.process()
            wl.update_seen(packet)

        return result


<<<<<<< HEAD
        This will get called when a packet is seen by a callsign
        registered in the watch list in the config file."""


class APRSDMessagePluginBase(metaclass=abc.ABCMeta):
=======
class APRSDRegexCommandPluginBase(APRSDPluginBase, metaclass=abc.ABCMeta):
>>>>>>> 2e7c884 (Refactor Message processing and MORE)
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

    @property
    def version(self):
        """Version"""
        raise NotImplementedError

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
                self.message_counter += 1
                result = self.process(packet)

<<<<<<< HEAD
        To reply with a message over the air, return a string
        to send.
        """
=======
        return result
>>>>>>> 2e7c884 (Refactor Message processing and MORE)


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
        :param module_class_string: full name of the class to create an object of
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
