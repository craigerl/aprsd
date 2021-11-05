import click


class AliasedGroup(click.Group):
    def command(self, *args, **kwargs):
        """A shortcut decorator for declaring and attaching a command to
        the group.  This takes the same arguments as :func:`command` but
        immediately registers the created command with this instance by
        calling into :meth:`add_command`.
        Copied from `click` and extended for `aliases`.
        """
        def decorator(f):
            aliases = kwargs.pop("aliases", [])
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
            aliases = kwargs.pop("aliases", [])
            cmd = click.decorators.group(*args, **kwargs)(f)
            self.add_command(cmd)
            for alias in aliases:
                self.add_command(cmd, name=alias)
            return cmd
        return decorator
