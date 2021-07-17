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
    def run(self, packet):
        """My special little hook that you can customize."""
        pass


class APRSDNotificationPluginBase(metaclass=abc.ABCMeta):
    """Base plugin class for all notification ased plugins.

    All these plugins will get every packet seen by APRSD's
    registered list of HAM callsigns in the config file's
    watch_list.

    When you want to 'notify' something when a packet is seen
    by a particular HAM callsign, write a plugin based off of
    this class.
    """

    def __init__(self, config):
        """The aprsd config object is stored."""
        self.config = config
        self.message_counter = 0

    @hookimpl
    def run(self, packet):
        return self.notify(packet)

    @abc.abstractmethod
    def notify(self, packet):
        """This is the main method called when a packet is rx.

        This will get called when a packet is seen by a callsign
        registered in the watch list in the config file."""
        pass


class APRSDMessagePluginBase(metaclass=abc.ABCMeta):
    """Base Message plugin class.

    When you want to search for a particular command in an
    APRSD message and send a direct reply, write a plugin
    based off of this class.
    """

    def __init__(self, config):
        """The aprsd config object is stored."""
        self.config = config
        self.message_counter = 0

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

    @property
    def message_count(self):
        return self.message_counter

    @hookimpl
    def run(self, packet):
        message = packet.get("message_text", None)
        if re.search(self.command_regex, message):
            self.message_counter += 1
            return self.command(packet)

    @abc.abstractmethod
    def command(self, packet):
        """This is the command that runs when the regex matches.

        To reply with a message over the air, return a string
        to send.
        """
        pass


class PluginManager:
    # The singleton instance object for this class
    _instance = None

    # the pluggy PluginManager for all Message plugins
    _pluggy_msg_pm = None

    # the pluggy PluginManager for all Notification plugins
    _pluggy_notify_pm = None

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
                                {"name": mem_name, "obj": obj(self.config)},
                            )

        return self.obj_list

    def is_plugin(self, obj):
        for c in inspect.getmro(obj):
            if issubclass(c, APRSDMessagePluginBase) or issubclass(
                c,
                APRSDNotificationPluginBase,
            ):
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
            module = importlib.reload(module)
        except Exception as ex:
            LOG.error("Failed to load Plugin '{}' : '{}'".format(module_name, ex))
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

    def _load_msg_plugin(self, plugin_name):
        """
        Given a python fully qualified class path.name,
        Try importing the path, then creating the object,
        then registering it as a aprsd Command Plugin
        """
        plugin_obj = None
        try:
            plugin_obj = self._create_class(
                plugin_name,
                APRSDMessagePluginBase,
                config=self.config,
            )
            if plugin_obj:
                LOG.info(
                    "Registering Message plugin '{}'({})  '{}'".format(
                        plugin_name,
                        plugin_obj.version,
                        plugin_obj.command_regex,
                    ),
                )
                self._pluggy_msg_pm.register(plugin_obj)
        except Exception as ex:
            LOG.exception("Couldn't load plugin '{}'".format(plugin_name), ex)

    def _load_notify_plugin(self, plugin_name):
        """
        Given a python fully qualified class path.name,
        Try importing the path, then creating the object,
        then registering it as a aprsd Command Plugin
        """
        plugin_obj = None
        try:
            plugin_obj = self._create_class(
                plugin_name,
                APRSDNotificationPluginBase,
                config=self.config,
            )
            if plugin_obj:
                LOG.info(
                    "Registering Notification plugin '{}'({})".format(
                        plugin_name,
                        plugin_obj.version,
                    ),
                )
                self._pluggy_notify_pm.register(plugin_obj)
        except Exception as ex:
            LOG.exception("Couldn't load plugin '{}'".format(plugin_name), ex)

    def reload_plugins(self):
        with self.lock:
            del self._pluggy_msg_pm
            del self._pluggy_notify_pm
            self.setup_plugins()

    def setup_plugins(self):
        """Create the plugin manager and register plugins."""

        LOG.info("Loading APRSD Message Plugins")
        enabled_msg_plugins = self.config["aprsd"].get("enabled_plugins", None)
        self._pluggy_msg_pm = pluggy.PluginManager("aprsd")
        self._pluggy_msg_pm.add_hookspecs(APRSDCommandSpec)
        if enabled_msg_plugins:
            for p_name in enabled_msg_plugins:
                self._load_msg_plugin(p_name)
        else:
            # Enabled plugins isn't set, so we default to loading all of
            # the core plugins.
            for p_name in CORE_MESSAGE_PLUGINS:
                self._load_plugin(p_name)

        if self.config["aprsd"]["watch_list"].get("enabled", False):
            LOG.info("Loading APRSD Notification Plugins")
            enabled_notify_plugins = self.config["aprsd"]["watch_list"].get(
                "enabled_plugins",
                None,
            )
            self._pluggy_notify_pm = pluggy.PluginManager("aprsd")
            self._pluggy_notify_pm.add_hookspecs(APRSDCommandSpec)
            if enabled_notify_plugins:
                for p_name in enabled_notify_plugins:
                    self._load_notify_plugin(p_name)

        else:
            LOG.info("Skipping Custom Plugins directory.")
        LOG.info("Completed Plugin Loading.")

    def run(self, packet):
        """Execute all the pluguns run method."""
        with self.lock:
            return self._pluggy_msg_pm.hook.run(packet=packet)

    def notify(self, packet):
        """Execute all the notify pluguns run method."""
        with self.lock:
            return self._pluggy_notify_pm.hook.run(packet=packet)

    def register_msg(self, obj):
        """Register the plugin."""
        self._pluggy_msg_pm.register(obj)

    def get_msg_plugins(self):
        return self._pluggy_msg_pm.get_plugins()
