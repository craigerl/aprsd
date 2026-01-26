import importlib.metadata as imp
import json
import logging
import sys

import click

from aprsd import cli_helper
from aprsd.main import cli

LOG = logging.getLogger('APRSD')


def _get_entry_points():
    """Get all oslo.config.opts entry points."""
    try:
        if sys.version_info < (3, 10):
            all_eps = imp.entry_points()
            selected = []
            if 'oslo.config.opts' in all_eps:
                for ep in all_eps['oslo.config.opts']:
                    if ep.group == 'oslo.config.opts':
                        selected.append(ep)
            return selected
        else:
            return imp.entry_points(group='oslo.config.opts')
    except Exception as e:
        LOG.warning(f'Failed to get entry points: {e}')
        return []


def _extract_package_name(entry_point_name):
    """Extract package name from entry point name.

    Examples:
    - 'aprsd.conf' -> 'aprsd'
    - 'aprsd_plugin_name.conf' -> 'aprsd_plugin_name'
    """
    if '.' in entry_point_name:
        return entry_point_name.rsplit('.', 1)[0]
    return entry_point_name


def _serialize_config_option(opt):
    """Convert an oslo.config option to a serializable dict."""
    opt_dict = {
        'name': opt.name,
        'type': type(opt).__name__,
        'help': getattr(opt, 'help', '') or '',
    }

    # Get default value if available
    if hasattr(opt, 'default'):
        default = opt.default
        # Handle callable defaults
        if callable(default):
            try:
                default = default()
            except Exception:
                default = None
        opt_dict['default'] = default
    else:
        opt_dict['default'] = None

    # Check if required (no default or default is None)
    opt_dict['required'] = not hasattr(opt, 'default') or opt_dict['default'] is None

    # Add additional attributes if available
    if hasattr(opt, 'choices') and opt.choices:
        opt_dict['choices'] = list(opt.choices)
    if hasattr(opt, 'secret') and opt.secret:
        opt_dict['secret'] = True
    if hasattr(opt, 'min') and opt.min is not None:
        opt_dict['min'] = opt.min
    if hasattr(opt, 'max') and opt.max is not None:
        opt_dict['max'] = opt.max

    return opt_dict


def get_plugin_config_options(plugins_only=False):
    """Discover all config options from installed plugin packages.

    Args:
        plugins_only: If True, exclude the built-in 'aprsd' package config.
    """
    entry_points = _get_entry_points()
    packages = {}

    for ep in entry_points:
        # Only process entry points that contain 'aprsd' in the name
        if 'aprsd' not in ep.name:
            continue

        package_name = _extract_package_name(ep.name)

        # Skip built-in aprsd config if plugins_only is True
        if plugins_only and package_name == 'aprsd':
            continue

        try:
            # Load the entry point and call list_opts()
            list_opts_func = ep.load()
            config_opts = list_opts_func()

            # config_opts can be a dict or a list of tuples
            if isinstance(config_opts, dict):
                # Convert dict to list of tuples for consistent processing
                config_opts = list(config_opts.items())
            elif not isinstance(config_opts, (list, tuple)):
                LOG.warning(
                    f'Entry point {ep.name} returned unexpected type: '
                    f'{type(config_opts)}',
                )
                continue

            # Process each config group
            package_config = {}
            for group_name, opt_list in config_opts:
                if not opt_list:
                    continue

                group_options = []
                for opt in opt_list:
                    opt_dict = _serialize_config_option(opt)
                    group_options.append(opt_dict)

                if group_options:
                    package_config[group_name] = group_options

            if package_config:
                packages[package_name] = package_config

        except Exception as e:
            LOG.warning(
                f'Failed to load config options from {ep.name}: {e}',
            )
            continue

    return packages


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    '--plugins-only',
    is_flag=True,
    default=False,
    help='Only export config options from installed plugins, excluding built-in aprsd config.',
)
@click.pass_context
@cli_helper.process_standard_options_no_config
def export_config(ctx, plugins_only):
    """Export all config options from installed APRSD plugins as JSON.

    This command discovers all installed APRSD plugin packages that have
    registered configuration options via oslo.config.opts entry points and
    builds a JSON output of all configuration options grouped by plugin package.

    Use --plugins-only to exclude the built-in aprsd configuration options
    and only show config from installed 3rd party plugins.
    """
    output = get_plugin_config_options(plugins_only=plugins_only)

    # Output as JSON
    click.echo(json.dumps(output, indent=2))
