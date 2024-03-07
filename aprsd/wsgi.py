import datetime
import importlib.metadata as imp
import io
import json
import logging
import time

import flask
from flask import Flask
from flask_httpauth import HTTPBasicAuth
from oslo_config import cfg, generator
import socketio
from werkzeug.security import check_password_hash

import aprsd
from aprsd import cli_helper, client, conf, packets, plugin, threads
from aprsd.log import log
from aprsd.rpc import client as aprsd_rpc_client


CONF = cfg.CONF
LOG = logging.getLogger("gunicorn.access")

auth = HTTPBasicAuth()
users = {}
app = Flask(
    "aprsd",
    static_url_path="/static",
    static_folder="web/admin/static",
    template_folder="web/admin/templates",
)
bg_thread = None
app.config["SECRET_KEY"] = "secret!"


# HTTPBasicAuth doesn't work on a class method.
# This has to be out here.  Rely on the APRSDFlask
# class to initialize the users from the config
@auth.verify_password
def verify_password(username, password):
    global users

    if username in users and check_password_hash(users.get(username), password):
        return username


def _stats():
    track = aprsd_rpc_client.RPCClient().get_packet_track()
    now = datetime.datetime.now()

    time_format = "%m-%d-%Y %H:%M:%S"

    stats_dict = aprsd_rpc_client.RPCClient().get_stats_dict()
    if not stats_dict:
        stats_dict = {
            "aprsd": {},
            "aprs-is": {"server": ""},
            "messages": {
                "sent": 0,
                "received": 0,
            },
            "email": {
                "sent": 0,
                "received": 0,
            },
            "seen_list": {
                "sent": 0,
                "received": 0,
            },
        }

    # Convert the watch_list entries to age
    wl = aprsd_rpc_client.RPCClient().get_watch_list()
    new_list = {}
    if wl:
        for call in wl.get_all():
            # call_date = datetime.datetime.strptime(
            #    str(wl.last_seen(call)),
            #    "%Y-%m-%d %H:%M:%S.%f",
            # )

            # We have to convert the RingBuffer to a real list
            # so that json.dumps works.
            # pkts = []
            # for pkt in wl.get(call)["packets"].get():
            #     pkts.append(pkt)

            new_list[call] = {
                "last": wl.age(call),
                # "packets": pkts
            }

    stats_dict["aprsd"]["watch_list"] = new_list
    packet_list = aprsd_rpc_client.RPCClient().get_packet_list()
    rx = tx = 0
    types = {}
    if packet_list:
        rx = packet_list.total_rx()
        tx = packet_list.total_tx()
        types_copy = packet_list.types.copy()

        for key in types_copy:
            types[str(key)] = dict(types_copy[key])

    stats_dict["packets"] = {
        "sent": tx,
        "received": rx,
        "types": types,
    }
    if track:
        size_tracker = len(track)
    else:
        size_tracker = 0

    result = {
        "time": now.strftime(time_format),
        "size_tracker": size_tracker,
        "stats": stats_dict,
    }

    return result


@app.route("/stats")
def stats():
    LOG.debug("/stats called")
    return json.dumps(_stats())


@app.route("/")
def index():
    stats = _stats()
    wl = aprsd_rpc_client.RPCClient().get_watch_list()
    if wl and wl.is_enabled():
        watch_count = len(wl)
        watch_age = wl.max_delta()
    else:
        watch_count = 0
        watch_age = 0

    sl = aprsd_rpc_client.RPCClient().get_seen_list()
    if sl:
        seen_count = len(sl)
    else:
        seen_count = 0

    pm = plugin.PluginManager()
    plugins = pm.get_plugins()
    plugin_count = len(plugins)

    if CONF.aprs_network.enabled:
        transport = "aprs-is"
        aprs_connection = (
            "APRS-IS Server: <a href='http://status.aprs2.net' >"
            "{}</a>".format(stats["stats"]["aprs-is"]["server"])
        )
    else:
        # We might be connected to a KISS socket?
        if client.KISSClient.kiss_enabled():
            transport = client.KISSClient.transport()
            if transport == client.TRANSPORT_TCPKISS:
                aprs_connection = (
                    "TCPKISS://{}:{}".format(
                        CONF.kiss_tcp.host,
                        CONF.kiss_tcp.port,
                    )
                )
            elif transport == client.TRANSPORT_SERIALKISS:
                aprs_connection = (
                    "SerialKISS://{}@{} baud".format(
                        CONF.kiss_serial.device,
                        CONF.kiss_serial.baudrate,
                    )
                )

    stats["transport"] = transport
    stats["aprs_connection"] = aprs_connection
    entries = conf.conf_to_dict()

    return flask.render_template(
        "index.html",
        initial_stats=stats,
        aprs_connection=aprs_connection,
        callsign=CONF.callsign,
        version=aprsd.__version__,
        config_json=json.dumps(
            entries, indent=4,
            sort_keys=True, default=str,
        ),
        watch_count=watch_count,
        watch_age=watch_age,
        seen_count=seen_count,
        plugin_count=plugin_count,
        # oslo_out=generate_oslo()
    )


@auth.login_required
def messages():
    track = packets.PacketTrack()
    msgs = []
    for id in track:
        LOG.info(track[id].dict())
        msgs.append(track[id].dict())

    return flask.render_template("messages.html", messages=json.dumps(msgs))


@auth.login_required
@app.route("/packets")
def get_packets():
    LOG.debug("/packets called")
    packet_list = aprsd_rpc_client.RPCClient().get_packet_list()
    if packet_list:
        tmp_list = []
        pkts = packet_list.copy()
        for key in pkts:
            pkt = packet_list.get(key)
            if pkt:
                tmp_list.append(pkt.json)

        return json.dumps(tmp_list)
    else:
        return json.dumps([])


@auth.login_required
@app.route("/plugins")
def plugins():
    LOG.debug("/plugins called")
    pm = plugin.PluginManager()
    pm.reload_plugins()

    return "reloaded"


def _get_namespaces():
    args = []

    all = imp.entry_points()
    selected = []
    if "oslo.config.opts" in all:
        for x in all["oslo.config.opts"]:
            if x.group == "oslo.config.opts":
                selected.append(x)
    for entry in selected:
        if "aprsd" in entry.name:
            args.append("--namespace")
            args.append(entry.name)

    return args


def generate_oslo():
    CONF.namespace = _get_namespaces()
    string_out = io.StringIO()
    generator.generate(CONF, string_out)
    return string_out.getvalue()


@auth.login_required
@app.route("/oslo")
def oslo():
    return generate_oslo()


@auth.login_required
@app.route("/save")
def save():
    """Save the existing queue to disk."""
    track = packets.PacketTrack()
    track.save()
    return json.dumps({"messages": "saved"})


class LogUpdateThread(threads.APRSDThread):

    def __init__(self):
        super().__init__("LogUpdate")

    def loop(self):
        if sio:
            log_entries = aprsd_rpc_client.RPCClient().get_log_entries()

            if log_entries:
                LOG.info(f"Sending log entries! {len(log_entries)}")
                for entry in log_entries:
                    sio.emit(
                        "log_entry", entry,
                        namespace="/logs",
                    )
        time.sleep(5)
        return True


class LoggingNamespace(socketio.Namespace):
    log_thread = None

    def on_connect(self, sid, environ):
        global sio
        LOG.debug(f"LOG on_connect {sid}")
        sio.emit(
            "connected", {"data": "/logs Connected"},
            namespace="/logs",
        )
        self.log_thread = LogUpdateThread()
        self.log_thread.start()

    def on_disconnect(self, sid):
        LOG.debug(f"LOG Disconnected {sid}")
        if self.log_thread:
            self.log_thread.stop()


def init_app(config_file=None, log_level=None):
    default_config_file = cli_helper.DEFAULT_CONFIG_FILE
    if not config_file:
        config_file = default_config_file

    CONF(
        [], project="aprsd", version=aprsd.__version__,
        default_config_files=[config_file],
    )

    if not log_level:
        log_level = CONF.logging.log_level

    return log_level


if __name__ == "__main__":
    async_mode = "threading"
    sio = socketio.Server(logger=True, async_mode=async_mode)
    app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)
    log_level = init_app(log_level="DEBUG")
    log.setup_logging(app, log_level)
    sio.register_namespace(LoggingNamespace("/logs"))
    CONF.log_opt_values(LOG, logging.DEBUG)
    app.run(
        threaded=True,
        debug=False,
        port=CONF.admin.web_port,
        host=CONF.admin.web_ip,
    )


if __name__ == "uwsgi_file_aprsd_wsgi":
    # Start with
    # uwsgi --http :8000 --gevent 1000 --http-websockets --master -w aprsd.wsgi --callable app

    async_mode = "gevent_uwsgi"
    sio = socketio.Server(logger=True, async_mode=async_mode)
    app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)
    log_level = init_app(
        log_level="DEBUG",
        config_file="/config/aprsd.conf",
        # Commented out for local development.
        # config_file=cli_helper.DEFAULT_CONFIG_FILE
    )
    log.setup_logging(app, log_level)
    sio.register_namespace(LoggingNamespace("/logs"))
    CONF.log_opt_values(LOG, logging.DEBUG)


if __name__ == "aprsd.wsgi":
    # set async_mode to 'threading', 'eventlet', 'gevent' or 'gevent_uwsgi' to
    # force a mode else, the best mode is selected automatically from what's
    # installed
    async_mode = "gevent_uwsgi"
    sio = socketio.Server(logger=True, async_mode=async_mode)
    app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

    log_level = init_app(
        log_level="DEBUG",
        config_file="/config/aprsd.conf",
        # config_file=cli_helper.DEFAULT_CONFIG_FILE,
    )
    log.setup_logging(app, log_level)
    sio.register_namespace(LoggingNamespace("/logs"))
    CONF.log_opt_values(LOG, logging.DEBUG)
