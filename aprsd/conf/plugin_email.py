from oslo_config import cfg


email_group = cfg.OptGroup(
    name="email_plugin",
    title="Options for the APRSD Email plugin",
)

email_opts = [
    cfg.StrOpt(
        "callsign",
        help="(Required) Callsign to validate for doing email commands."
             "Only this callsign can check email. This is also where the "
             "email notifications for new emails will be sent.",
    ),
    cfg.BoolOpt(
        "enabled",
        default=False,
        help="Enable the Email plugin?",
    ),
    cfg.BoolOpt(
        "debug",
        default=False,
        help="Enable the Email plugin Debugging?",
    ),
]

email_imap_opts = [
    cfg.StrOpt(
        "imap_login",
        help="Login username/email for IMAP server",
    ),
    cfg.StrOpt(
        "imap_password",
        secret=True,
        help="Login password for IMAP server",
    ),
    cfg.HostnameOpt(
        "imap_host",
        help="Hostname/IP of the IMAP server",
    ),
    cfg.PortOpt(
        "imap_port",
        default=993,
        help="Port to use for IMAP server",
    ),
    cfg.BoolOpt(
        "imap_use_ssl",
        default=True,
        help="Use SSL for connection to IMAP Server",
    ),
]

email_smtp_opts = [
    cfg.StrOpt(
        "smtp_login",
        help="Login username/email for SMTP server",
    ),
    cfg.StrOpt(
        "smtp_password",
        secret=True,
        help="Login password for SMTP server",
    ),
    cfg.HostnameOpt(
        "smtp_host",
        help="Hostname/IP of the SMTP server",
    ),
    cfg.PortOpt(
        "smtp_port",
        default=465,
        help="Port to use for SMTP server",
    ),
    cfg.BoolOpt(
        "smtp_use_ssl",
        default=True,
        help="Use SSL for connection to SMTP Server",
    ),
]

email_shortcuts_opts = [
    cfg.ListOpt(
        "email_shortcuts",
        help="List of email shortcuts for checking/sending email "
             "For Exmaple: wb=walt@walt.com,cl=cl@cl.com\n"
             "Means use 'wb' to send an email to walt@walt.com",
    ),
]

ALL_OPTS = (
    email_opts
    + email_imap_opts
    + email_smtp_opts
    + email_shortcuts_opts
)


def register_opts(config):
    config.register_group(email_group)
    config.register_opts(ALL_OPTS, group=email_group)


def list_opts():
    return {
        email_group.name: ALL_OPTS,
    }
