import inspect
import logging

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from aprsd import cli_helper
from aprsd import plugin as aprsd_plugin
from aprsd.main import cli
from aprsd.plugins import fortune, notify, ping, time, version, weather
from aprsd.utils import package as aprsd_package

LOG = logging.getLogger('APRSD')


def show_built_in_plugins(console):
    modules = [fortune, notify, ping, time, version, weather]
    plugins = []

    for module in modules:
        entries = inspect.getmembers(module, inspect.isclass)
        for entry in entries:
            cls = entry[1]
            if issubclass(cls, aprsd_plugin.APRSDPluginBase):
                info = {
                    'name': cls.__qualname__,
                    'path': f'{cls.__module__}.{cls.__qualname__}',
                    'version': cls.version,
                    'docstring': cls.__doc__,
                    'short_desc': cls.short_description,
                }

                if issubclass(cls, aprsd_plugin.APRSDRegexCommandPluginBase):
                    info['command_regex'] = cls.command_regex
                    info['type'] = 'RegexCommand'

                if issubclass(cls, aprsd_plugin.APRSDWatchListPluginBase):
                    info['type'] = 'WatchList'

                plugins.append(info)

    plugins = sorted(plugins, key=lambda i: i['name'])

    table = Table(
        title='[not italic]:snake:[/] [bold][magenta]APRSD Built-in Plugins [not italic]:snake:[/]',
    )
    table.add_column('Plugin Name', style='cyan', no_wrap=True)
    table.add_column('Info', style='bold yellow')
    table.add_column('Type', style='bold green')
    table.add_column('Plugin Path', style='bold blue')
    for entry in plugins:
        table.add_row(entry['name'], entry['short_desc'], entry['type'], entry['path'])

    console.print(table)


def show_pypi_plugins(installed_plugins, console):
    packages = aprsd_package.get_pypi_packages()

    title = Text.assemble(
        ('Pypi.org APRSD Installable Plugin Packages\n\n', 'bold magenta'),
        ('Install any of the following plugins with\n', 'bold yellow'),
        ("'pip install ", 'bold white'),
        ("<Plugin Package Name>'", 'cyan'),
    )

    table = Table(title=title)
    table.add_column('Plugin Package Name', style='cyan', no_wrap=True)
    table.add_column('Description', style='yellow')
    table.add_column('Version', style='yellow', justify='center')
    table.add_column('Released', style='bold green', justify='center')
    table.add_column('Installed?', style='red', justify='center')
    emoji = ':open_file_folder:'
    for package in packages:
        link = package['info']['package_url']
        version = package['info']['version']
        package_name = package['info']['name']
        description = package['info']['summary']
        created = package['releases'][version][0]['upload_time']

        if 'aprsd-' not in package_name or '-plugin' not in package_name:
            continue

        under = package_name.replace('-', '_')
        installed = 'Yes' if under in installed_plugins else 'No'
        table.add_row(
            f'[link={link}]{emoji}[/link] {package_name}',
            description,
            version,
            created,
            installed,
        )

    console.print('\n')
    console.print(table)


def show_pypi_extensions(installed_extensions, console):
    packages = aprsd_package.get_pypi_packages()

    title = Text.assemble(
        ('Pypi.org APRSD Installable Extension Packages\n\n', 'bold magenta'),
        ('Install any of the following extensions by running\n', 'bold yellow'),
        ("'pip install ", 'bold white'),
        ("<Plugin Package Name>'", 'cyan'),
    )
    table = Table(title=title)
    table.add_column('Extension Package Name', style='cyan', no_wrap=True)
    table.add_column('Description', style='yellow')
    table.add_column('Version', style='yellow', justify='center')
    table.add_column('Released', style='bold green', justify='center')
    table.add_column('Installed?', style='red', justify='center')
    emoji = ':open_file_folder:'

    for package in packages:
        link = package['info']['package_url']
        version = package['info']['version']
        package_name = package['info']['name']
        description = package['info']['summary']
        created = package['releases'][version][0]['upload_time']
        if 'aprsd-' not in package_name or '-extension' not in package_name:
            continue

        under = package_name.replace('-', '_')
        installed = 'Yes' if under in installed_extensions else 'No'
        table.add_row(
            f'[link={link}]{emoji}[/link] {package_name}',
            description,
            version,
            created,
            installed,
        )

    console.print('\n')
    console.print(table)


def show_installed_plugins(installed_plugins, console):
    if not installed_plugins:
        return

    table = Table(
        title='[not italic]:snake:[/] [bold][magenta]APRSD Installed 3rd party Plugins [not italic]:snake:[/]',
    )
    table.add_column('Package Name', style=' bold white', no_wrap=True)
    table.add_column('Plugin Name', style='cyan', no_wrap=True)
    table.add_column('Version', style='yellow', justify='center')
    table.add_column('Type', style='bold green')
    table.add_column('Plugin Path', style='bold blue')
    for name in installed_plugins:
        for plugin in installed_plugins[name]:
            table.add_row(
                name.replace('_', '-'),
                plugin['name'],
                plugin['version'],
                aprsd_package.plugin_type(plugin['obj']),
                plugin['path'],
            )

    console.print('\n')
    console.print(table)


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.pass_context
@cli_helper.process_standard_options_no_config
def list_plugins(ctx):
    """List the built in plugins available to APRSD."""
    console = Console()

    with console.status('Show Built-in Plugins') as status:
        show_built_in_plugins(console)

        status.update('Fetching pypi.org plugins')
        installed_plugins = aprsd_package.get_installed_plugins()
        show_pypi_plugins(installed_plugins, console)

        status.update('Looking for installed APRSD plugins')
        show_installed_plugins(installed_plugins, console)


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.pass_context
@cli_helper.process_standard_options_no_config
def list_extensions(ctx):
    """List the built in plugins available to APRSD."""
    console = Console()

    with console.status('Show APRSD Extensions') as status:
        status.update('Fetching pypi.org APRSD Extensions')

        status.update('Looking for installed APRSD Extensions')
        installed_extensions = aprsd_package.get_installed_extensions()
        show_pypi_extensions(installed_extensions, console)
