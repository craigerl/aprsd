import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import time

import flask
from flask.logging import default_handler
import flask_classful
from flask_httpauth import HTTPBasicAuth
from flask_socketio import Namespace, SocketIO
from oslo_config import cfg
from werkzeug.security import check_password_hash, generate_password_hash

import aprsd
from aprsd import cli_helper, client, conf, packets, plugin, threads
from aprsd.logging import rich as aprsd_logging
from aprsd.rpc import client as aprsd_rpc_client


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")

auth = HTTPBasicAuth()
users = None
app = None


# HTTPBasicAuth doesn't work on a class method.
# This has to be out here.  Rely on the APRSDFlask
# class to initialize the users from the config
@auth.verify_password
def verify_password(username, password):
    global users

    if username in users and check_password_hash(users.get(username), password):
        return username


class APRSDFlask(flask_classful.FlaskView):

    def set_config(self):
        global users
        self.users = {}
        user = CONF.admin.user
        self.users[user] = generate_password_hash(CONF.admin.password)
        users = self.users

    @auth.login_required
    def index(self):
        stats = self._stats()
        print(stats)
        LOG.debug(
            "watch list? {}".format(
                CONF.watch_list.callsigns,
            ),
        )
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
        )

    @auth.login_required
    def messages(self):
        track = packets.PacketTrack()
        msgs = []
        for id in track:
            LOG.info(track[id].dict())
            msgs.append(track[id].dict())

        return flask.render_template("messages.html", messages=json.dumps(msgs))

    @auth.login_required
    def packets(self):
        packet_list = aprsd_rpc_client.RPCClient().get_packet_list()
        if packet_list:
            packets = packet_list.get()
            tmp_list = []
            for pkt in packets:
                tmp_list.append(pkt.json)

            return json.dumps(tmp_list)
        else:
            return json.dumps([])

    @auth.login_required
    def plugins(self):
        pm = plugin.PluginManager()
        pm.reload_plugins()

        return "reloaded"

    @auth.login_required
    def save(self):
        """Save the existing queue to disk."""
        track = packets.PacketTrack()
        track.save()
        return json.dumps({"messages": "saved"})

    def _stats(self):
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
        if packet_list:
            rx = packet_list.total_rx()
            tx = packet_list.total_tx()
        stats_dict["packets"] = {
            "sent": tx,
            "received": rx,
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

    def stats(self):
        return json.dumps(self._stats())


class LogUpdateThread(threads.APRSDThread):

    def __init__(self):
        super().__init__("LogUpdate")

    def loop(self):
        global socketio

        if socketio:
            log_entries = aprsd_rpc_client.RPCClient().get_log_entries()

            if log_entries:
                for entry in log_entries:
                    socketio.emit(
                        "log_entry", entry,
                        namespace="/logs",
                    )

        time.sleep(5)
        return True


class LoggingNamespace(Namespace):
    log_thread = None

    def on_connect(self):
        global socketio
        socketio.emit(
            "connected", {"data": "/logs Connected"},
            namespace="/logs",
        )
        self.log_thread = LogUpdateThread()
        self.log_thread.start()

    def on_disconnect(self):
        LOG.debug("LOG Disconnected")
        if self.log_thread:
            self.log_thread.stop()


def setup_logging(flask_app, loglevel, quiet):
    flask_log = logging.getLogger("werkzeug")
    flask_app.logger.removeHandler(default_handler)
    flask_log.removeHandler(default_handler)

    log_level = conf.log.LOG_LEVELS[loglevel]
    flask_log.setLevel(log_level)
    date_format = CONF.logging.date_format
    flask_log.disabled = True
    flask_app.logger.disabled = True

    if CONF.logging.rich_logging:
        log_format = "%(message)s"
        log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
        rh = aprsd_logging.APRSDRichHandler(
            show_thread=True, thread_width=15,
            rich_tracebacks=True, omit_repeated_times=False,
        )
        rh.setFormatter(log_formatter)
        flask_log.addHandler(rh)

    log_file = CONF.logging.logfile

    if log_file:
        log_format = CONF.logging.logformat
        log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
        fh = RotatingFileHandler(
            log_file, maxBytes=(10248576 * 5),
            backupCount=4,
        )
        fh.setFormatter(log_formatter)
        flask_log.addHandler(fh)


def init_flask(loglevel, quiet):
    global socketio

    flask_app = flask.Flask(
        "aprsd",
        static_url_path="/static",
        static_folder="web/admin/static",
        template_folder="web/admin/templates",
    )
    setup_logging(flask_app, loglevel, quiet)
    server = APRSDFlask()
    server.set_config()
    flask_app.route("/", methods=["GET"])(server.index)
    flask_app.route("/stats", methods=["GET"])(server.stats)
    flask_app.route("/messages", methods=["GET"])(server.messages)
    flask_app.route("/packets", methods=["GET"])(server.packets)
    flask_app.route("/save", methods=["GET"])(server.save)
    flask_app.route("/plugins", methods=["GET"])(server.plugins)

    socketio = SocketIO(
        flask_app, logger=False, engineio_logger=False,
        # async_mode="threading",
    )
    #    import eventlet
    #    eventlet.monkey_patch()
    gunicorn_logger = logging.getLogger("gunicorn.error")
    flask_app.logger.handlers = gunicorn_logger.handlers
    flask_app.logger.setLevel(gunicorn_logger.level)

    socketio.on_namespace(LoggingNamespace("/logs"))
    return socketio, flask_app


if __name__ == "aprsd.flask":
    try:
        default_config_file = cli_helper.DEFAULT_CONFIG_FILE
        CONF(
            [], project="aprsd", version=aprsd.__version__,
            default_config_files=[default_config_file],
        )
    except cfg.ConfigFilesNotFoundError:
        pass
    sio, app = init_flask("DEBUG", False)
