import click
import click_completion

from aprsd.main import cli


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@cli.group(help="Click Completion subcommands", context_settings=CONTEXT_SETTINGS)
@click.pass_context
def completion(ctx):
    pass


# show dumps out the completion code for a particular shell
@completion.command(help="Show completion code for shell", name="show")
@click.option("-i", "--case-insensitive/--no-case-insensitive", help="Case insensitive completion")
@click.argument("shell", required=False, type=click_completion.DocumentedChoice(click_completion.core.shells))
def show(shell, case_insensitive):
    """Show the click-completion-command completion code"""
    extra_env = {"_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE": "ON"} if case_insensitive else {}
    click.echo(click_completion.core.get_code(shell, extra_env=extra_env))


# install will install the completion code for a particular shell
@completion.command(help="Install completion code for a shell", name="install")
@click.option("--append/--overwrite", help="Append the completion code to the file", default=None)
@click.option("-i", "--case-insensitive/--no-case-insensitive", help="Case insensitive completion")
@click.argument("shell", required=False, type=click_completion.DocumentedChoice(click_completion.core.shells))
@click.argument("path", required=False)
def install(append, case_insensitive, shell, path):
    """Install the click-completion-command completion"""
    extra_env = {"_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE": "ON"} if case_insensitive else {}
    shell, path = click_completion.core.install(shell=shell, path=path, append=append, extra_env=extra_env)
    click.echo(f"{shell} completion installed in {path}")
