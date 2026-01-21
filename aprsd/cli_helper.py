import cProfile
import logging
import typing as t
from functools import update_wrapper
from pathlib import Path

import click
from oslo_config import cfg

import aprsd
from aprsd import conf  # noqa: F401
from aprsd.log import log
from aprsd.utils import trace

CONF = cfg.CONF
home = str(Path.home())
DEFAULT_CONFIG_DIR = f'{home}/.config/aprsd/'
DEFAULT_SAVE_FILE = f'{home}/.config/aprsd/aprsd.p'
DEFAULT_CONFIG_FILE = f'{home}/.config/aprsd/aprsd.conf'


F = t.TypeVar('F', bound=t.Callable[..., t.Any])

log_options = [
    click.option(
        '--show-thread',
        default=False,
        is_flag=True,
        help='Show thread name in log format (disabled by default for listen).',
    ),
    click.option(
        '--show-level',
        default=False,
        is_flag=True,
        help='Show log level in log format (disabled by default for listen).',
    ),
    click.option(
        '--show-location',
        default=False,
        is_flag=True,
        help='Show location in log format (disabled by default for listen).',
    ),
]

common_options = [
    click.option(
        '--loglevel',
        default='INFO',
        show_default=True,
        type=click.Choice(
            ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
            case_sensitive=False,
        ),
        show_choices=True,
        help='The log level to use for aprsd.log',
    ),
    click.option(
        '-c',
        '--config',
        'config_file',
        show_default=True,
        default=DEFAULT_CONFIG_FILE,
        help='The aprsd config file to use for options.',
    ),
    click.option(
        '--quiet',
        is_flag=True,
        default=False,
        help="Don't log to stdout",
    ),
    click.option(
        '--profile',
        'profile_output',
        default=None,
        required=False,
        metavar='FILENAME',
        help='Enable profiling and save results to FILENAME. '
        'If FILENAME is not provided, defaults to aprsd_profile.prof',
    ),
] + log_options


class AliasedGroup(click.Group):
    def command(self, *args, **kwargs):
        """A shortcut decorator for declaring and attaching a command to
        the group.  This takes the same arguments as :func:`command` but
        immediately registers the created command with this instance by
        calling into :meth:`add_command`.
        Copied from `click` and extended for `aliases`.
        """

        def decorator(f):
            aliases = kwargs.pop('aliases', [])
            cmd = click.decorators.command(*args, **kwargs)(f)
            self.add_command(cmd)
            for alias in aliases:
                self.add_command(cmd, name=alias)
            return cmd

        return decorator

    def group(self, *args, **kwargs):
        """A shortcut decorator for declaring and attaching a group to
        the group.  This takes the same arguments as :func:`group` but
        immediately registers the created command with this instance by
        calling into :meth:`add_command`.
        Copied from `click` and extended for `aliases`.
        """

        def decorator(f):
            aliases = kwargs.pop('aliases', [])
            cmd = click.decorators.group(*args, **kwargs)(f)
            self.add_command(cmd)
            for alias in aliases:
                self.add_command(cmd, name=alias)
            return cmd

        return decorator


def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


def setup_logging_with_options(
    show_thread: bool,
    show_level: bool,
    show_location: bool,
    loglevel: str,
    quiet: bool,
) -> None:
    """Setup logging with custom format based on show_thread and show_level options.

    Args:
        show_thread: Whether to include thread name in log format
        show_level: Whether to include log level in log format
        loglevel: The log level to use
        quiet: Whether to suppress stdout logging
        include_location: Whether to include location info in log format (default True)
    """
    # Build custom log format based on show_thread and show_level options
    from aprsd.conf import log as conf_log

    parts = []
    # Timestamp is always included
    parts.append(conf_log.DEFAULT_LOG_FORMAT_TIMESTAMP)

    if show_thread:
        parts.append(conf_log.DEFAULT_LOG_FORMAT_THREAD)

    if show_level:
        parts.append(conf_log.DEFAULT_LOG_FORMAT_LEVEL)

    # Message is always included
    parts.append(conf_log.DEFAULT_LOG_FORMAT_MESSAGE)

    if show_location:
        parts.append(conf_log.DEFAULT_LOG_FORMAT_LOCATION)

    # Set the custom log format
    CONF.logging.logformat = ' | '.join(parts)

    # Now call setup_logging with our modified config
    log.setup_logging(loglevel, quiet)


def process_standard_options(f: F) -> F:
    def new_func(*args, **kwargs):
        ctx = args[0]
        ctx.ensure_object(dict)
        config_file_found = True

        # Extract show_thread and show_level
        show_thread = kwargs.get('show_thread', False)
        show_level = kwargs.get('show_level', False)
        show_location = kwargs.get('show_location', False)

        if kwargs['config_file']:
            default_config_files = [kwargs['config_file']]
        else:
            default_config_files = None

        try:
            CONF(
                [],
                project='aprsd',
                version=aprsd.__version__,
                default_config_files=default_config_files,
            )
        except cfg.ConfigFilesNotFoundError:
            config_file_found = False
        except cfg.RequiredOptError as roe:
            import sys

            LOG = logging.getLogger('APRSD')  # noqa: N806
            LOG.error(f'A Required option is missing in the config file : {roe}')
            # If the missing option is callsign or owner_callsign, give specific message
            if 'owner_callsign' in str(roe):
                LOG.error(
                    'The "owner_callsign" option is required. '
                    'It is used to identify the licensed ham radio operator '
                    'responsible for this APRSD instance, which may be different than '
                    'the "callsign" used by APRSD for messaging.',
                )
            sys.exit(-1)

        ctx.obj['loglevel'] = kwargs['loglevel']
        # ctx.obj["config_file"] = kwargs["config_file"]
        ctx.obj['quiet'] = kwargs['quiet']

        # NOW modify config AFTER CONF is initialized but BEFORE setup_logging
        setup_logging_with_options(
            show_thread=show_thread,
            show_level=show_level,
            show_location=show_location,
            loglevel=ctx.obj['loglevel'],
            quiet=ctx.obj['quiet'],
        )
        if CONF.trace_enabled:
            trace.setup_tracing(['method', 'api'])

        if not config_file_found:
            LOG = logging.getLogger('APRSD')  # noqa: N806
            LOG.error("No config file found!! run 'aprsd sample-config'")

        profile_output = kwargs.pop('profile_output', None)
        del kwargs['loglevel']
        del kwargs['config_file']
        del kwargs['quiet']
        del kwargs['show_thread']
        del kwargs['show_level']
        del kwargs['show_location']

        # Enable profiling if requested
        if profile_output is not None:
            # If profile_output is empty string, use default filename
            if not profile_output or profile_output == '':
                profile_output = 'aprsd_profile.prof'
            profiler = cProfile.Profile()
            profiler.enable()
            try:
                result = f(*args, **kwargs)
            finally:
                profiler.disable()
                profiler.dump_stats(profile_output)
                LOG = logging.getLogger('APRSD')  # noqa: N806
                LOG.info(f'Profile data saved to {profile_output}')
                LOG.info(f'Analyze with: python -m pstats {profile_output}')
                LOG.info(f'Or visualize with: snakeviz {profile_output}')
            return result
        else:
            return f(*args, **kwargs)

    return update_wrapper(t.cast(F, new_func), f)


def process_standard_options_no_config(f: F) -> F:
    """Use this as a decorator when config isn't needed."""

    def new_func(*args, **kwargs):
        ctx = args[0]
        ctx.ensure_object(dict)

        # Extract show_thread and show_level
        show_thread = kwargs.get('show_thread', False)
        show_level = kwargs.get('show_level', False)
        show_location = kwargs.get('show_location', False)

        # Initialize CONF without config file for log format access
        try:
            CONF(
                [],
                project='aprsd',
                version=aprsd.__version__,
                default_config_files=None,
            )
        except cfg.ConfigFilesNotFoundError:
            # Config file not needed for this function, so ignore error
            pass
        except cfg.RequiredOptError:
            # They are missing a required option from the config,
            # but we don't care, because they aren't loading a config
            pass

        ctx.obj['loglevel'] = kwargs['loglevel']
        ctx.obj['config_file'] = kwargs['config_file']
        ctx.obj['quiet'] = kwargs['quiet']

        # NOW modify config AFTER CONF is initialized but BEFORE setup_logging
        setup_logging_with_options(
            show_thread=show_thread,
            show_level=show_level,
            show_location=show_location,
            loglevel=ctx.obj['loglevel'],
            quiet=ctx.obj['quiet'],
        )

        profile_output = kwargs.pop('profile_output', None)
        del kwargs['loglevel']
        del kwargs['config_file']
        del kwargs['quiet']
        del kwargs['show_thread']
        del kwargs['show_level']
        del kwargs['show_location']

        # Enable profiling if requested
        if profile_output is not None:
            # If profile_output is empty string, use default filename
            if not profile_output or profile_output == '':
                profile_output = 'aprsd_profile.prof'
            profiler = cProfile.Profile()
            profiler.enable()
            try:
                result = f(*args, **kwargs)
            finally:
                profiler.disable()
                profiler.dump_stats(profile_output)
                LOG = logging.getLogger('APRSD')  # noqa: N806
                LOG.info(f'Profile data saved to {profile_output}')
                LOG.info(f'Analyze with: python -m pstats {profile_output}')
                LOG.info(f'Or visualize with: snakeviz {profile_output}')
            return result
        else:
            return f(*args, **kwargs)

    return update_wrapper(t.cast(F, new_func), f)
