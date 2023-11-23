from oslo_config import cfg


aprsfi_group = cfg.OptGroup(
    name="aprs_fi",
    title="APRS.FI website settings",
)
query_group = cfg.OptGroup(
    name="query_plugin",
    title="Options for the Query Plugin",
)
avwx_group = cfg.OptGroup(
    name="avwx_plugin",
    title="Options for the AVWXWeatherPlugin",
)
owm_wx_group = cfg.OptGroup(
    name="owm_weather_plugin",
    title="Options for the OWMWeatherPlugin",
)

location_group = cfg.OptGroup(
    name="location_plugin",
    title="Options for the LocationPlugin",
)

aprsfi_opts = [
    cfg.StrOpt(
        "apiKey",
        help="Get the apiKey from your aprs.fi account here:"
             "http://aprs.fi/account",
    ),
]

query_plugin_opts = [
    cfg.StrOpt(
        "callsign",
        help="The Ham callsign to allow access to the query plugin from RF.",
    ),
]

owm_wx_opts = [
    cfg.StrOpt(
        "apiKey",
        help="OWMWeatherPlugin api key to OpenWeatherMap's API."
             "This plugin uses the openweathermap API to fetch"
             "location and weather information."
             "To use this plugin you need to get an openweathermap"
             "account and apikey."
             "https://home.openweathermap.org/api_keys",
    ),
]

avwx_opts = [
    cfg.StrOpt(
        "apiKey",
        help="avwx-api is an opensource project that has"
             "a hosted service here: https://avwx.rest/"
             "You can launch your own avwx-api in a container"
             "by cloning the githug repo here:"
             "https://github.com/avwx-rest/AVWX-API",
    ),
    cfg.StrOpt(
        "base_url",
        default="https://avwx.rest",
        help="The base url for the avwx API.  If you are hosting your own"
             "Here is where you change the url to point to yours.",
    ),
]

location_opts = [
    cfg.StrOpt(
        "geopy_geocoder",
        choices=[
            "ArcGIS", "AzureMaps", "Baidu", "Bing", "GoogleV3", "HERE",
            "Nominatim", "OpenCage", "TomTom", "USGov", "What3Words", "Woosmap",
        ],
        default="Nominatim",
        help="The geopy geocoder to use.  Default is Nominatim."
             "See https://geopy.readthedocs.io/en/stable/#module-geopy.geocoders"
             "for more information.",
    ),
    cfg.StrOpt(
        "user_agent",
        default="APRSD",
        help="The user agent to use for the Nominatim geocoder."
             "See https://geopy.readthedocs.io/en/stable/#module-geopy.geocoders"
             "for more information.",
    ),
    cfg.StrOpt(
        "arcgis_username",
        default=None,
        help="The username to use for the ArcGIS geocoder."
             "See https://geopy.readthedocs.io/en/latest/#arcgis"
             "for more information."
             "Only used for the ArcGIS geocoder.",
    ),
    cfg.StrOpt(
        "arcgis_password",
        default=None,
        help="The password to use for the ArcGIS geocoder."
             "See https://geopy.readthedocs.io/en/latest/#arcgis"
             "for more information."
             "Only used for the ArcGIS geocoder.",
    ),
    cfg.StrOpt(
        "azuremaps_subscription_key",
        help="The subscription key to use for the AzureMaps geocoder."
             "See https://geopy.readthedocs.io/en/latest/#azuremaps"
             "for more information."
             "Only used for the AzureMaps geocoder.",
    ),
    cfg.StrOpt(
        "baidu_api_key",
        help="The API key to use for the Baidu geocoder."
             "See https://geopy.readthedocs.io/en/latest/#baidu"
             "for more information."
             "Only used for the Baidu geocoder.",
    ),
    cfg.StrOpt(
        "bing_api_key",
        help="The API key to use for the Bing geocoder."
             "See https://geopy.readthedocs.io/en/latest/#bing"
             "for more information."
             "Only used for the Bing geocoder.",
    ),
    cfg.StrOpt(
        "google_api_key",
        help="The API key to use for the Google geocoder."
             "See https://geopy.readthedocs.io/en/latest/#googlev3"
             "for more information."
             "Only used for the Google geocoder.",
    ),
    cfg.StrOpt(
        "here_api_key",
        help="The API key to use for the HERE geocoder."
             "See https://geopy.readthedocs.io/en/latest/#here"
             "for more information."
             "Only used for the HERE geocoder.",
    ),
    cfg.StrOpt(
        "opencage_api_key",
        help="The API key to use for the OpenCage geocoder."
             "See https://geopy.readthedocs.io/en/latest/#opencage"
             "for more information."
             "Only used for the OpenCage geocoder.",
    ),
    cfg.StrOpt(
        "tomtom_api_key",
        help="The API key to use for the TomTom geocoder."
             "See https://geopy.readthedocs.io/en/latest/#tomtom"
             "for more information."
             "Only used for the TomTom geocoder.",
    ),
    cfg.StrOpt(
        "what3words_api_key",
        help="The API key to use for the What3Words geocoder."
             "See https://geopy.readthedocs.io/en/latest/#what3words"
             "for more information."
             "Only used for the What3Words geocoder.",
    ),
    cfg.StrOpt(
        "woosmap_api_key",
        help="The API key to use for the Woosmap geocoder."
             "See https://geopy.readthedocs.io/en/latest/#woosmap"
             "for more information."
             "Only used for the Woosmap geocoder.",
    ),
]


def register_opts(config):
    config.register_group(aprsfi_group)
    config.register_opts(aprsfi_opts, group=aprsfi_group)
    config.register_group(query_group)
    config.register_opts(query_plugin_opts, group=query_group)
    config.register_group(owm_wx_group)
    config.register_opts(owm_wx_opts, group=owm_wx_group)
    config.register_group(avwx_group)
    config.register_opts(avwx_opts, group=avwx_group)
    config.register_group(location_group)
    config.register_opts(location_opts, group=location_group)


def list_opts():
    return {
        aprsfi_group.name: aprsfi_opts,
        query_group.name: query_plugin_opts,
        owm_wx_group.name: owm_wx_opts,
        avwx_group.name: avwx_opts,
        location_group.name: location_opts,
    }
