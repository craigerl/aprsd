import datetime
import importlib.metadata as imp
import io
import json
import logging
import queue

import flask
from flask import Flask, request
from flask_httpauth import HTTPBasicAuth
from oslo_config import cfg, generator
import socketio
from werkzeug.security import check_password_hash

import aprsd
from aprsd import cli_helper, client, conf, packets, plugin, threads
from aprsd.log import log
from aprsd.threads import stats as stats_threads
from aprsd.utils import json as aprsd_json


CONF = cfg.CONF
LOG = logging.getLogger("gunicorn.access")
logging_queue = queue.Queue()

auth = HTTPBasicAuth()
users: dict[str, str] = {}
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
    stats_obj = stats_threads.StatsStore()
    stats_obj.load()
    now = datetime.datetime.now()
    time_format = "%m-%d-%Y %H:%M:%S"
    stats = {
        "time": now.strftime(time_format),
        "stats": stats_obj.data,
    }
    return stats


@app.route("/stats")
def stats():
    LOG.debug("/stats called")
    return json.dumps(_stats(), cls=aprsd_json.SimpleJSONEncoder)


@app.route("/")
def index():
    stats = _stats()
    pm = plugin.PluginManager()
    plugins = pm.get_plugins()
    plugin_count = len(plugins)
    client_stats = stats["stats"].get("APRSClientStats", {})

    if CONF.aprs_network.enabled:
        transport = "aprs-is"
        if client_stats:
            aprs_connection = client_stats.get("server_string", "")
        else:
            aprs_connection = "APRS-IS"
        aprs_connection = (
            "APRS-IS Server: <a href='http://status.aprs2.net' >"
            "{}</a>".format(aprs_connection)
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

    if client_stats:
        stats["stats"]["APRSClientStats"]["transport"] = transport
        stats["stats"]["APRSClientStats"]["aprs_connection"] = aprs_connection
    entries = conf.conf_to_dict()

    thread_info = stats["stats"].get("APRSDThreadList", {})
    if thread_info:
        thread_count = len(thread_info)
    else:
        thread_count = "unknown"

    return flask.render_template(
        "index.html",
        initial_stats=json.dumps(stats, cls=aprsd_json.SimpleJSONEncoder),
        aprs_connection=aprs_connection,
        callsign=CONF.callsign,
        version=aprsd.__version__,
        config_json=json.dumps(
            entries, indent=4,
            sort_keys=True, default=str,
        ),
        plugin_count=plugin_count,
        thread_count=thread_count,
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
    stats = _stats()
    stats_dict = stats["stats"]
    packets = stats_dict.get("PacketList", {})
    return json.dumps(packets, cls=aprsd_json.SimpleJSONEncoder)


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


@app.route("/log_entries", methods=["POST"])
def log_entries():
    """The url that the server can call to update the logs."""
    entries = request.json
    LOG.info(f"Log entries called {len(entries)}")
    for entry in entries:
        logging_queue.put(entry)
    return json.dumps({"messages": "saved"})


class LogUpdateThread(threads.APRSDThread):

    def __init__(self, logging_queue=None):
        super().__init__("LogUpdate")
        self.logging_queue = logging_queue

    def loop(self):
        if sio:
            try:
                log_entry = self.logging_queue.get(block=True, timeout=1)
                if log_entry:
                    sio.emit(
                        "log_entry",
                        log_entry,
                        namespace="/logs",
                    )
            except queue.Empty:
                pass
        return True


class LoggingNamespace(socketio.Namespace):
    log_thread = None

    def on_connect(self, sid, environ):
        global sio, logging_queue
        LOG.info(f"LOG on_connect {sid}")
        sio.emit(
            "connected", {"data": "/logs Connected"},
            namespace="/logs",
        )
        self.log_thread = LogUpdateThread(logging_queue=logging_queue)
        self.log_thread.start()

    def on_disconnect(self, sid):
        LOG.info(f"LOG Disconnected {sid}")
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
    log_level = init_app()
    log.setup_logging(log_level)
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
        # log_level="DEBUG",
        config_file="/config/aprsd.conf",
        # Commented out for local development.
        # config_file=cli_helper.DEFAULT_CONFIG_FILE
    )
    log.setup_logging(log_level)
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
        # log_level="DEBUG",
        config_file="/config/aprsd.conf",
        # config_file=cli_helper.DEFAULT_CONFIG_FILE,
    )
    log.setup_logging(log_level)
    sio.register_namespace(LoggingNamespace("/logs"))
    CONF.log_opt_values(LOG, logging.DEBUG)
