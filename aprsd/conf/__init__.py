from oslo_config import cfg

from aprsd.conf import client, common, log, plugin_common, plugin_email


CONF = cfg.CONF

log.register_opts(CONF)
common.register_opts(CONF)
client.register_opts(CONF)

# plugins
plugin_common.register_opts(CONF)
plugin_email.register_opts(CONF)


def set_lib_defaults():
    """Update default value for configuration options from other namespace.
    Example, oslo lib config options. This is needed for
    config generator tool to pick these default value changes.
    https://docs.openstack.org/oslo.config/latest/cli/
    generator.html#modifying-defaults-from-other-namespaces
    """

    # Update default value of oslo_log default_log_levels and
    # logging_context_format_string config option.
    set_log_defaults()


def set_log_defaults():
    # log.set_defaults(default_log_levels=log.get_default_log_levels())
    pass


def conf_to_dict():
    """Convert the CONF options to a single level dictionary."""
    entries = {}

    def _sanitize(opt, value):
        """Obfuscate values of options declared secret."""
        return value if not opt.secret else "*" * 4

    for opt_name in sorted(CONF._opts):
        opt = CONF._get_opt_info(opt_name)["opt"]
        val = str(_sanitize(opt, getattr(CONF, opt_name)))
        entries[str(opt)] = val

    for group_name in list(CONF._groups):
        group_attr = CONF.GroupAttr(CONF, CONF._get_group(group_name))
        for opt_name in sorted(CONF._groups[group_name]._opts):
            opt = CONF._get_opt_info(opt_name, group_name)["opt"]
            val = str(_sanitize(opt, getattr(group_attr, opt_name)))
            gname_opt_name = f"{group_name}.{opt_name}"
            entries[gname_opt_name] = val

    return entries
