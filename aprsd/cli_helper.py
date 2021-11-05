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


class GroupWithCommandOptions(click.Group):
    """ Allow application of options to group with multi command """

    def add_command(self, cmd, name=None):
        click.Group.add_command(self, cmd, name=name)

        # add the group parameters to the command
        for param in self.params:
            cmd.params.append(param)

        # hook the commands invoke with our own
        cmd.invoke = self.build_command_invoke(cmd.invoke)
        self.invoke_without_command = True

    def build_command_invoke(self, original_invoke):

        def command_invoke(ctx):
            """ insert invocation of group function """

            # separate the group parameters
            ctx.obj = dict(_params={})
            for param in self.params:
                name = param.name
                if name in ctx.params:
                    ctx.obj["_params"][name] = ctx.params[name]
                    del ctx.params[name]

            # call the group function with its parameters
            params = ctx.params
            ctx.params = ctx.obj["_params"]
            self.invoke(ctx)
            ctx.params = params

            # now call the original invoke(the command)
            original_invoke(ctx)

        return command_invoke
