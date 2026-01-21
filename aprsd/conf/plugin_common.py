from oslo_config import cfg

aprsfi_group = cfg.OptGroup(
    name='aprs_fi',
    title='APRS.FI website settings',
)
avwx_group = cfg.OptGroup(
    name='avwx_plugin',
    title='Options for the AVWXWeatherPlugin',
)

aprsfi_opts = [
    cfg.StrOpt(
        'apiKey',
        help='Get the apiKey from your aprs.fi account here:http://aprs.fi/account',
    ),
]

avwx_opts = [
    cfg.StrOpt(
        'apiKey',
        help='avwx-api is an opensource project that has'
        'a hosted service here: https://avwx.rest/'
        'You can launch your own avwx-api in a container'
        'by cloning the githug repo here:'
        'https://github.com/avwx-rest/AVWX-API',
    ),
    cfg.StrOpt(
        'base_url',
        default='https://avwx.rest',
        help='The base url for the avwx API.  If you are hosting your own'
        'Here is where you change the url to point to yours.',
    ),
]


def register_opts(config):
    config.register_group(aprsfi_group)
    config.register_opts(aprsfi_opts, group=aprsfi_group)
    config.register_group(avwx_group)
    config.register_opts(avwx_opts, group=avwx_group)


def list_opts():
    return {
        aprsfi_group.name: aprsfi_opts,
        avwx_group.name: avwx_opts,
    }
