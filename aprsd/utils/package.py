import fnmatch
import importlib
import inspect
import logging
import os
import pkgutil
import sys
from traceback import print_tb

import requests
from thesmuggler import smuggle

from aprsd import plugin as aprsd_plugin

LOG = logging.getLogger()


def onerror(name):
    type, value, traceback = sys.exc_info()
    print_tb(traceback)


def plugin_type(obj):
    for c in inspect.getmro(obj):
        if issubclass(c, aprsd_plugin.APRSDRegexCommandPluginBase):
            return 'RegexCommand'
        if issubclass(c, aprsd_plugin.APRSDWatchListPluginBase):
            return 'WatchList'
        if issubclass(c, aprsd_plugin.APRSDPluginBase):
            return 'APRSDPluginBase'

    return 'Unknown'


def is_plugin(obj):
    for c in inspect.getmro(obj):
        if issubclass(c, aprsd_plugin.APRSDPluginBase):
            return True

    return False


def walk_package(package):
    return pkgutil.walk_packages(
        package.__path__,
        package.__name__ + '.',
        onerror=onerror,
    )


def get_module_info(package_name, module_name, module_path):
    if not os.path.exists(module_path):
        return None

    dir_path = os.path.realpath(module_path)
    pattern = '*.py'

    obj_list = []

    for path, _subdirs, files in os.walk(dir_path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                module = smuggle(f'{path}/{name}')
                for mem_name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and is_plugin(obj):
                        obj_list.append(
                            {
                                'package': package_name,
                                'name': mem_name,
                                'obj': obj,
                                'version': obj.version,
                                'path': f'{".".join([module_name, obj.__name__])}',
                            },
                        )

    return obj_list


def is_aprsd_package(name):
    if name.startswith('aprsd_'):
        return True


def is_aprsd_extension(name):
    if name.startswith('aprsd_') and 'extension' in name:
        # This is an installed package that is an extension of
        # APRSD
        return True
    else:
        # We might have an editable install of an extension
        # of APRSD.
        return '__editable__' in name and 'aprsd_' in name and 'extension' in name


def get_installed_aprsd_items():
    # installed plugins
    plugins = {}
    extensions = {}
    for _finder, name, ispkg in pkgutil.iter_modules():
        if ispkg and is_aprsd_package(name):
            module = importlib.import_module(name)
            pkgs = walk_package(module)
            for pkg in pkgs:
                pkg_info = get_module_info(
                    module.__name__, pkg.name, module.__path__[0]
                )
                if 'plugin' in name:
                    plugins[name] = pkg_info
                elif 'extension' in name:
                    mod = importlib.import_module(name)
                    extensions[name] = mod
        elif is_aprsd_extension(name):
            # This isn't a package, so it could be an editable install
            module = importlib.import_module(name)
            key_name = next(iter(module.MAPPING.keys()))
            module = importlib.import_module(key_name)
            pkg_info = get_module_info(module.__name__, key_name, module.__path__[0])
            extensions[key_name] = module
    return plugins, extensions


def get_installed_plugins():
    # installed plugins
    plugins, _ = get_installed_aprsd_items()
    return plugins


def get_installed_extensions():
    # installed plugins
    _, extensions = get_installed_aprsd_items()
    return extensions


def get_pypi_packages():
    if simple_r := requests.get(
        'https://pypi.org/simple',
        headers={'Accept': 'application/vnd.pypi.simple.v1+json'},
    ):
        simple_response = simple_r.json()
    else:
        simple_response = {}

    key = 'aprsd'
    matches = [
        p['name'] for p in simple_response['projects'] if p['name'].startswith(key)
    ]

    packages = []
    for pkg in matches:
        # Get info for first match
        if r := requests.get(
            f'https://pypi.org/pypi/{pkg}/json',
            headers={'Accept': 'application/json'},
        ):
            packages.append(r.json())

    return packages


def log_installed_extensions_and_plugins():
    plugins, extensions = get_installed_aprsd_items()

    for name in extensions:
        ext = extensions[name]
        # print(f"Extension: {ext}")
        # print(f"Extension: {ext.__dict__}")
        if hasattr(ext, '__version__'):
            version = ext.__version__
        elif hasattr(ext, 'version'):
            version = ext.version
        else:
            version = ext['version']
        LOG.info(f'Extension: {name} version: {version}')

    for plugin in plugins:
        LOG.info(f'Plugin: {plugin} version: {plugins[plugin][0]["version"]}')
