from oslo_config import cfg

aprsfi_group = cfg.OptGroup(
    name='aprs_fi',
    title='APRS.FI website settings',
)

aprsfi_opts = [
    cfg.StrOpt(
        'apiKey',
        help='Get the apiKey from your aprs.fi account here:http://aprs.fi/account',
    ),
]


def register_opts(config):
    config.register_group(aprsfi_group)
    config.register_opts(aprsfi_opts, group=aprsfi_group)


def list_opts():
    return {
        aprsfi_group.name: aprsfi_opts,
    }
