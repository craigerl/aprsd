import fnmatch
import importlib
import inspect
import logging
import os
import pkgutil
import re
import sys
from traceback import print_tb
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import click
import requests
from rich.console import Console
from rich.table import Table
from rich.text import Text
from thesmuggler import smuggle

from aprsd import cli_helper
from aprsd import plugin as aprsd_plugin
from aprsd.main import cli
from aprsd.plugins import (
    email, fortune, location, notify, ping, query, time, version, weather,
)


LOG = logging.getLogger("APRSD")
PYPI_URL = "https://pypi.org/search/"


def onerror(name):
    print(f"Error importing module {name}")
    type, value, traceback = sys.exc_info()
    print_tb(traceback)


def is_plugin(obj):
    for c in inspect.getmro(obj):
        if issubclass(c, aprsd_plugin.APRSDPluginBase):
            return True

    return False


def plugin_type(obj):
    for c in inspect.getmro(obj):
        if issubclass(c, aprsd_plugin.APRSDRegexCommandPluginBase):
            return "RegexCommand"
        if issubclass(c, aprsd_plugin.APRSDWatchListPluginBase):
            return "WatchList"
        if issubclass(c, aprsd_plugin.APRSDPluginBase):
            return "APRSDPluginBase"

    return "Unknown"


def walk_package(package):
    return pkgutil.walk_packages(
        package.__path__,
        package.__name__ + ".",
        onerror=onerror,
    )


def get_module_info(package_name, module_name, module_path):
    if not os.path.exists(module_path):
        return None

    dir_path = os.path.realpath(module_path)
    pattern = "*.py"

    obj_list = []

    for path, _subdirs, files in os.walk(dir_path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                module = smuggle(f"{path}/{name}")
                for mem_name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and is_plugin(obj):
                        obj_list.append(
                            {
                                "package": package_name,
                                "name": mem_name, "obj": obj,
                                "version": obj.version,
                                "path": f"{'.'.join([module_name, obj.__name__])}",
                            },
                        )

    return obj_list


def _get_installed_aprsd_items():
    # installed plugins
    plugins = {}
    extensions = {}
    for finder, name, ispkg in pkgutil.iter_modules():
        if name.startswith("aprsd_"):
            print(f"Found aprsd_ module: {name}")
            if ispkg:
                module = importlib.import_module(name)
                pkgs = walk_package(module)
                for pkg in pkgs:
                    pkg_info = get_module_info(module.__name__, pkg.name, module.__path__[0])
                    if "plugin" in name:
                        plugins[name] = pkg_info
                    elif "extension" in name:
                        extensions[name] = pkg_info
    return plugins, extensions


def get_installed_plugins():
    # installed plugins
    plugins, extensions = _get_installed_aprsd_items()
    return plugins


def get_installed_extensions():
    # installed plugins
    plugins, extensions = _get_installed_aprsd_items()
    return extensions


def show_built_in_plugins(console):
    modules = [email, fortune, location, notify, ping, query, time, version, weather]
    plugins = []

    for module in modules:
        entries = inspect.getmembers(module, inspect.isclass)
        for entry in entries:
            cls = entry[1]
            if issubclass(cls, aprsd_plugin.APRSDPluginBase):
                info = {
                    "name": cls.__qualname__,
                    "path": f"{cls.__module__}.{cls.__qualname__}",
                    "version": cls.version,
                    "docstring": cls.__doc__,
                    "short_desc": cls.short_description,
                }

                if issubclass(cls, aprsd_plugin.APRSDRegexCommandPluginBase):
                    info["command_regex"] = cls.command_regex
                    info["type"] = "RegexCommand"

                if issubclass(cls, aprsd_plugin.APRSDWatchListPluginBase):
                    info["type"] = "WatchList"

                plugins.append(info)

    plugins = sorted(plugins, key=lambda i: i["name"])

    table = Table(
        title="[not italic]:snake:[/] [bold][magenta]APRSD Built-in Plugins [not italic]:snake:[/]",
    )
    table.add_column("Plugin Name", style="cyan", no_wrap=True)
    table.add_column("Info", style="bold yellow")
    table.add_column("Type", style="bold green")
    table.add_column("Plugin Path", style="bold blue")
    for entry in plugins:
        table.add_row(entry["name"], entry["short_desc"], entry["type"], entry["path"])

    console.print(table)


def _get_pypi_packages():
    query = "aprsd"
    snippets = []
    s = requests.Session()
    for page in range(1, 3):
        params = {"q": query, "page": page}
        r = s.get(PYPI_URL, params=params)
        soup = BeautifulSoup(r.text, "html.parser")
        snippets += soup.select('a[class*="snippet"]')
        if not hasattr(s, "start_url"):
            s.start_url = r.url.rsplit("&page", maxsplit=1).pop(0)

    return snippets


def show_pypi_plugins(installed_plugins, console):
    snippets = _get_pypi_packages()

    title = Text.assemble(
        ("Pypi.org APRSD Installable Plugin Packages\n\n", "bold magenta"),
        ("Install any of the following plugins with\n", "bold yellow"),
        ("'pip install ", "bold white"),
        ("<Plugin Package Name>'", "cyan"),
    )

    table = Table(title=title)
    table.add_column("Plugin Package Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="yellow")
    table.add_column("Version", style="yellow", justify="center")
    table.add_column("Released", style="bold green", justify="center")
    table.add_column("Installed?", style="red", justify="center")
    for snippet in snippets:
        link = urljoin(PYPI_URL, snippet.get("href"))
        package = re.sub(r"\s+", " ", snippet.select_one('span[class*="name"]').text.strip())
        version = re.sub(r"\s+", " ", snippet.select_one('span[class*="version"]').text.strip())
        created = re.sub(r"\s+", " ", snippet.select_one('span[class*="created"]').text.strip())
        description = re.sub(r"\s+", " ", snippet.select_one('p[class*="description"]').text.strip())
        emoji = ":open_file_folder:"

        if "aprsd-" not in package or "-plugin" not in package:
            continue

        under = package.replace("-", "_")
        if under in installed_plugins:
            installed = "Yes"
        else:
            installed = "No"

        table.add_row(
            f"[link={link}]{emoji}[/link] {package}",
            description, version, created, installed,
        )

    console.print("\n")
    console.print(table)


def show_pypi_extensions(installed_extensions, console):
    snippets = _get_pypi_packages()

    title = Text.assemble(
        ("Pypi.org APRSD Installable Extension Packages\n\n", "bold magenta"),
        ("Install any of the following extensions by running\n", "bold yellow"),
        ("'pip install ", "bold white"),
        ("<Plugin Package Name>'", "cyan"),
    )
    table = Table(title=title)
    table.add_column("Extension Package Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="yellow")
    table.add_column("Version", style="yellow", justify="center")
    table.add_column("Released", style="bold green", justify="center")
    table.add_column("Installed?", style="red", justify="center")
    for snippet in snippets:
        link = urljoin(PYPI_URL, snippet.get("href"))
        package = re.sub(r"\s+", " ", snippet.select_one('span[class*="name"]').text.strip())
        version = re.sub(r"\s+", " ", snippet.select_one('span[class*="version"]').text.strip())
        created = re.sub(r"\s+", " ", snippet.select_one('span[class*="created"]').text.strip())
        description = re.sub(r"\s+", " ", snippet.select_one('p[class*="description"]').text.strip())
        emoji = ":open_file_folder:"

        if "aprsd-" not in package or "-extension" not in package:
            continue

        under = package.replace("-", "_")
        if under in installed_extensions:
            installed = "Yes"
        else:
            installed = "No"

        table.add_row(
            f"[link={link}]{emoji}[/link] {package}",
            description, version, created, installed,
        )

    console.print("\n")
    console.print(table)


def show_installed_plugins(installed_plugins, console):
    if not installed_plugins:
        return

    table = Table(
        title="[not italic]:snake:[/] [bold][magenta]APRSD Installed 3rd party Plugins [not italic]:snake:[/]",
    )
    table.add_column("Package Name", style=" bold white", no_wrap=True)
    table.add_column("Plugin Name", style="cyan", no_wrap=True)
    table.add_column("Version", style="yellow", justify="center")
    table.add_column("Type", style="bold green")
    table.add_column("Plugin Path", style="bold blue")
    for name in installed_plugins:
        for plugin in installed_plugins[name]:
            table.add_row(
                name.replace("_", "-"),
                plugin["name"],
                plugin["version"],
                plugin_type(plugin["obj"]),
                plugin["path"],
            )

    console.print("\n")
    console.print(table)


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.pass_context
@cli_helper.process_standard_options_no_config
def list_plugins(ctx):
    """List the built in plugins available to APRSD."""
    console = Console()

    with console.status("Show Built-in Plugins") as status:
        show_built_in_plugins(console)

        status.update("Fetching pypi.org plugins")
        installed_plugins = get_installed_plugins()
        show_pypi_plugins(installed_plugins, console)

        status.update("Looking for installed APRSD plugins")
        show_installed_plugins(installed_plugins, console)


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.pass_context
@cli_helper.process_standard_options_no_config
def list_extensions(ctx):
    """List the built in plugins available to APRSD."""
    console = Console()

    with console.status("Show APRSD Extensions") as status:
        status.update("Fetching pypi.org APRSD Extensions")
        installed_extensions = get_installed_extensions()
        show_pypi_extensions(installed_extensions, console)
