from pathlib import Path

from oslo_config import cfg


home = str(Path.home())
DEFAULT_CONFIG_DIR = f"{home}/.config/aprsd/"
APRSD_DEFAULT_MAGIC_WORD = "CHANGEME!!!"

admin_group = cfg.OptGroup(
    name="admin",
    title="Admin web interface settings",
)
watch_list_group = cfg.OptGroup(
    name="watch_list",
    title="Watch List settings",
)
rpc_group = cfg.OptGroup(
    name="rpc_settings",
    title="RPC Settings for admin <--> web",
)


aprsd_opts = [
    cfg.StrOpt(
        "callsign",
        required=True,
        help="Callsign to use for messages sent by APRSD",
    ),
    cfg.BoolOpt(
        "enable_save",
        default=True,
        help="Enable saving of watch list, packet tracker between restarts.",
    ),
    cfg.StrOpt(
        "save_location",
        default=DEFAULT_CONFIG_DIR,
        help="Save location for packet tracking files.",
    ),
    cfg.BoolOpt(
        "trace_enabled",
        default=False,
        help="Enable code tracing",
    ),
    cfg.StrOpt(
        "units",
        default="imperial",
        help="Units for display, imperial or metric",
    ),
    cfg.IntOpt(
        "ack_rate_limit_period",
        default=1,
        help="The wait period in seconds per Ack packet being sent."
             "1 means 1 ack packet per second allowed."
             "2 means 1 pack packet every 2 seconds allowed",
    ),
    cfg.IntOpt(
        "msg_rate_limit_period",
        default=2,
        help="Wait period in seconds per non AckPacket being sent."
             "2 means 1 packet every 2 seconds allowed."
             "5 means 1 pack packet every 5 seconds allowed",
    ),
]

watch_list_opts = [
    cfg.BoolOpt(
        "enabled",
        default=False,
        help="Enable the watch list feature.  Still have to enable "
             "the correct plugin.  Built-in plugin to use is "
             "aprsd.plugins.notify.NotifyPlugin",
    ),
    cfg.ListOpt(
        "callsigns",
        help="Callsigns to watch for messsages",
    ),
    cfg.StrOpt(
        "alert_callsign",
        help="The Ham Callsign to send messages to for watch list alerts.",
    ),
    cfg.IntOpt(
        "packet_keep_count",
        default=10,
        help="The number of packets to store.",
    ),
    cfg.IntOpt(
        "alert_time_seconds",
        default=3600,
        help="Time to wait before alert is sent on new message for "
             "users in callsigns.",
    ),
]

admin_opts = [
    cfg.BoolOpt(
        "web_enabled",
        default=False,
        help="Enable the Admin Web Interface",
    ),
    cfg.IPOpt(
        "web_ip",
        default="0.0.0.0",
        help="The ip address to listen on",
    ),
    cfg.PortOpt(
        "web_port",
        default=8001,
        help="The port to listen on",
    ),
    cfg.StrOpt(
        "user",
        default="admin",
        help="The admin user for the admin web interface",
    ),
    cfg.StrOpt(
        "password",
        secret=True,
        help="Admin interface password",
    ),
]

rpc_opts = [
    cfg.BoolOpt(
        "enabled",
        default=True,
        help="Enable RPC calls",
    ),
    cfg.StrOpt(
        "ip",
        default="localhost",
        help="The ip address to listen on",
    ),
    cfg.PortOpt(
        "port",
        default=18861,
        help="The port to listen on",
    ),
    cfg.StrOpt(
        "magic_word",
        default=APRSD_DEFAULT_MAGIC_WORD,
        help="Magic word to authenticate requests between client/server",
    ),
]

enabled_plugins_opts = [
    cfg.ListOpt(
        "enabled_plugins",
        default=[
            "aprsd.plugins.email.EmailPlugin",
            "aprsd.plugins.fortune.FortunePlugin",
            "aprsd.plugins.location.LocationPlugin",
            "aprsd.plugins.ping.PingPlugin",
            "aprsd.plugins.query.QueryPlugin",
            "aprsd.plugins.time.TimePlugin",
            "aprsd.plugins.weather.OWMWeatherPlugin",
            "aprsd.plugins.version.VersionPlugin",
            "aprsd.plugins.notify.NotifySeenPlugin",
        ],
        help="Comma separated list of enabled plugins for APRSD."
             "To enable installed external plugins add them here."
             "The full python path to the class name must be used",
    ),
]


def register_opts(config):
    config.register_opts(aprsd_opts)
    config.register_opts(enabled_plugins_opts)
    config.register_group(admin_group)
    config.register_opts(admin_opts, group=admin_group)
    config.register_group(watch_list_group)
    config.register_opts(watch_list_opts, group=watch_list_group)
    config.register_group(rpc_group)
    config.register_opts(rpc_opts, group=rpc_group)


def list_opts():
    return {
        "DEFAULT": (aprsd_opts + enabled_plugins_opts),
        admin_group.name: admin_opts,
        watch_list_group.name: watch_list_opts,
        rpc_group.name: rpc_opts,
    }
