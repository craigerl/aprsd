# The base plugin class
import abc
import fnmatch
import importlib
import inspect
import logging
import os
import re

import pluggy
from thesmuggler import smuggle

# setup the global logger
LOG = logging.getLogger("APRSD")

hookspec = pluggy.HookspecMarker("aprsd")
hookimpl = pluggy.HookimplMarker("aprsd")

CORE_PLUGINS = [
    "aprsd.plugins.email.EmailPlugin",
    "aprsd.plugins.fortune.FortunePlugin",
    "aprsd.plugins.location.LocationPlugin",
    "aprsd.plugins.ping.PingPlugin",
    "aprsd.plugins.query.QueryPlugin",
    "aprsd.plugins.time.TimePlugin",
    "aprsd.plugins.weather.USWeatherPlugin",
    "aprsd.plugins.version.VersionPlugin",
]


class APRSDCommandSpec:
    """A hook specification namespace."""

    @hookspec
    def run(self, fromcall, message, ack):
        """My special little hook that you can customize."""
        pass


class APRSDPluginBase(metaclass=abc.ABCMeta):
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


class PluginManager:
    # The singleton instance object for this class
    _instance = None

    # the pluggy PluginManager
    _pluggy_pm = None

    # aprsd config dict
    config = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
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
                                {"name": mem_name, "obj": obj(self.config)},
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
                    "Registering Command plugin '{}'({})  '{}'".format(
                        plugin_name,
                        plugin_obj.version,
                        plugin_obj.command_regex,
                    ),
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
                                o["name"],
                                o["obj"].version,
                                o["obj"].command_regex,
                            ),
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
