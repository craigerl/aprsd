import click
import click.shell_completion

from aprsd import cli_helper
from aprsd.main import cli

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.argument(
    'shell', type=click.Choice(list(click.shell_completion._available_shells))
)
@cli_helper.process_standard_options_no_config
def completion(ctx, shell):
    """Show the shell completion code"""
    from click.utils import _detect_program_name

    cls = click.shell_completion.get_completion_class(shell)
    prog_name = _detect_program_name()
    complete_var = f'_{prog_name}_COMPLETE'.replace('-', '_').upper()
    print(cls(cli, {}, prog_name, complete_var).source())
    print(
        '# Add the following line to your shell configuration file to have aprsd command line completion'
    )
    print("# but remove the leading '#' character.")
    print(f'# eval "$(aprsd completion {shell})"')
