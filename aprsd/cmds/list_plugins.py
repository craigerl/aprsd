import inspect
import logging
from textwrap import indent

import click
from tabulate import tabulate

from aprsd import cli_helper, plugin
from aprsd.plugins import (
    email, fortune, location, notify, ping, query, time, version, weather,
)

from ..aprsd import cli


LOG = logging.getLogger("APRSD")


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.pass_context
@cli_helper.process_standard_options_no_config
def list_plugins(ctx):
    """List the built in plugins available to APRSD."""

    modules = [email, fortune, location, notify, ping, query, time, version, weather]
    plugins = []

    for module in modules:
        entries = inspect.getmembers(module, inspect.isclass)
        for entry in entries:
            cls = entry[1]
            if issubclass(cls, plugin.APRSDPluginBase):
                info = {
                    "name": cls.__qualname__,
                    "path": f"{cls.__module__}.{cls.__qualname__}",
                    "version": cls.version,
                    "docstring": cls.__doc__,
                    "short_desc": cls.short_description,
                }

                if issubclass(cls, plugin.APRSDRegexCommandPluginBase):
                    info["command_regex"] = cls.command_regex
                    info["type"] = "RegexCommand"

                if issubclass(cls, plugin.APRSDWatchListPluginBase):
                    info["type"] = "WatchList"

                plugins.append(info)

    lines = []
    headers = ("Plugin Name", "Plugin Path", "Type", "Info")

    for entry in plugins:
        lines.append(
            (entry["name"], entry["path"], entry["type"], entry["short_desc"]),
        )

    click.echo(indent(tabulate(lines, headers, disable_numparse=True), " "))
