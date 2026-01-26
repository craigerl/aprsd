import inspect
import json
import logging

import click

from aprsd import cli_helper
from aprsd import plugin as aprsd_plugin
from aprsd.main import cli
from aprsd.plugins import fortune, notify, ping, time, version, weather
from aprsd.utils import package as aprsd_package

LOG = logging.getLogger('APRSD')


def get_built_in_plugins():
    """Discover all built-in APRSD plugins."""
    modules = [fortune, notify, ping, time, version, weather]
    plugins = []

    for module in modules:
        entries = inspect.getmembers(module, inspect.isclass)
        for entry in entries:
            cls = entry[1]
            if issubclass(cls, aprsd_plugin.APRSDPluginBase):
                plugin_info = {
                    'package': 'aprsd',
                    'class_name': cls.__qualname__,
                    'path': f'{cls.__module__}.{cls.__qualname__}',
                    'version': cls.version,
                    'base_class_type': aprsd_package.plugin_type(cls),
                }

                # If it's a regex command plugin, include the command_regex
                if issubclass(cls, aprsd_plugin.APRSDRegexCommandPluginBase):
                    # Try to get command_regex from the class
                    # It's typically defined as a class attribute in plugin implementations
                    try:
                        # Check the MRO to find where command_regex is actually defined
                        cmd_regex = None
                        for base_cls in inspect.getmro(cls):
                            if 'command_regex' in base_cls.__dict__:
                                attr = base_cls.__dict__['command_regex']
                                # If it's not a property descriptor, use it
                                if not isinstance(attr, property):
                                    cmd_regex = attr
                                    break
                        plugin_info['command_regex'] = cmd_regex
                    except Exception:
                        plugin_info['command_regex'] = None

                plugins.append(plugin_info)

    return plugins


def get_installed_plugin_classes():
    """Discover all installed 3rd party plugin classes, grouped by package."""
    installed_plugins = aprsd_package.get_installed_plugins()
    packages = {}

    for package_name, plugin_list in installed_plugins.items():
        if not plugin_list:
            continue

        package_plugins = []
        for plugin_info in plugin_list:
            plugin_class = plugin_info['obj']
            plugin_data = {
                'class_name': plugin_info['name'],
                'path': plugin_info['path'],
                'version': plugin_info['version'],
                'base_class_type': aprsd_package.plugin_type(plugin_class),
            }

            # If it's a regex command plugin, include the command_regex
            if issubclass(plugin_class, aprsd_plugin.APRSDRegexCommandPluginBase):
                # Try to get command_regex from the class
                # It's typically defined as a class attribute in plugin implementations
                try:
                    # Check the MRO to find where command_regex is actually defined
                    cmd_regex = None
                    for base_cls in inspect.getmro(plugin_class):
                        if 'command_regex' in base_cls.__dict__:
                            attr = base_cls.__dict__['command_regex']
                            # If it's not a property descriptor, use it
                            if not isinstance(attr, property):
                                cmd_regex = attr
                                break
                    plugin_data['command_regex'] = cmd_regex
                except Exception:
                    plugin_data['command_regex'] = None

            package_plugins.append(plugin_data)

        if package_plugins:
            packages[package_name] = package_plugins

    return packages


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.pass_context
@cli_helper.process_standard_options_no_config
def export_plugins(ctx):
    """Export all installed APRSD plugins as JSON.

    This command discovers all installed APRSD plugin packages and builds
    a JSON output of each plugin class associated with the plugin package.
    For each plugin class it includes the base class type, and if it's an
    APRSDRegexCommandPluginBase class, it includes the command_regex.
    """
    output = {
        'built_in_plugins': [],
        'installed_plugins': {},
    }

    # Get built-in plugins
    built_in = get_built_in_plugins()
    output['built_in_plugins'] = built_in

    # Get installed 3rd party plugins (grouped by package)
    installed = get_installed_plugin_classes()
    output['installed_plugins'] = installed

    # Output as JSON
    click.echo(json.dumps(output, indent=2))
