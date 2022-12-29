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
import rpyc
from werkzeug.security import check_password_hash, generate_password_hash

import aprsd
from aprsd import cli_helper, client, conf, packets, plugin, threads
from aprsd.conf import common
from aprsd.logging import rich as aprsd_logging


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")

auth = HTTPBasicAuth()
users = None
app = None


class AuthSocketStream(rpyc.SocketStream):
    """Used to authenitcate the RPC stream to remote."""

    @classmethod
    def connect(cls, *args, authorizer=None, **kwargs):
        stream_obj = super().connect(*args, **kwargs)

        if callable(authorizer):
            authorizer(stream_obj.sock)

        return stream_obj


# HTTPBasicAuth doesn't work on a class method.
# This has to be out here.  Rely on the APRSDFlask
# class to initialize the users from the config
@auth.verify_password
def verify_password(username, password):
    global users

    if username in users and check_password_hash(users.get(username), password):
        return username


class RPCClient:
    _instance = None
    _rpc_client = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._check_settings()
        self.get_rpc_client()

    def _check_settings(self):
        if not CONF.rpc_settings.enabled:
            LOG.error("RPC is not enabled, no way to get stats!!")

        if CONF.rpc_settings.magic_word == common.APRSD_DEFAULT_MAGIC_WORD:
            LOG.warning("You are using the default RPC magic word!!!")
            LOG.warning("edit aprsd.conf and change rpc_settings.magic_word")

    def _rpyc_connect(
        self, host, port,
        service=rpyc.VoidService,
        config={}, ipv6=False,
        keepalive=False, authorizer=None,
    ):

        print(f"Connecting to RPC host {host}:{port}")
        try:
            s = AuthSocketStream.connect(
                host, port, ipv6=ipv6, keepalive=keepalive,
                authorizer=authorizer,
            )
            return rpyc.utils.factory.connect_stream(s, service, config=config)
        except ConnectionRefusedError:
            LOG.error(f"Failed to connect to RPC host {host}")
            return None

    def get_rpc_client(self):
        if not self._rpc_client:
            magic = CONF.rpc_settings.magic_word
            self._rpc_client = self._rpyc_connect(
                CONF.rpc_settings.ip,
                CONF.rpc_settings.port,
                authorizer=lambda sock: sock.send(magic.encode()),
            )
        return self._rpc_client

    def get_stats_dict(self):
        cl = self.get_rpc_client()
        result = {}
        if not cl:
            return result

        try:
            rpc_stats_dict = cl.root.get_stats()
            result = json.loads(rpc_stats_dict)
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_packet_track(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result = cl.root.get_packet_track()
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_packet_list(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result = cl.root.get_packet_list()
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_watch_list(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result = cl.root.get_watch_list()
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_seen_list(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result = cl.root.get_seen_list()
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_log_entries(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result_str = cl.root.get_log_entries()
            result = json.loads(result_str)
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result


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
        wl = RPCClient().get_watch_list()
        if wl and wl.is_enabled():
            watch_count = len(wl)
            watch_age = wl.max_delta()
        else:
            watch_count = 0
            watch_age = 0

        sl = RPCClient().get_seen_list()
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
        packet_list = RPCClient().get_packet_list()
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
        track = RPCClient().get_packet_track()
        now = datetime.datetime.now()

        time_format = "%m-%d-%Y %H:%M:%S"

        stats_dict = RPCClient().get_stats_dict()
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
        wl = RPCClient().get_watch_list()
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
        packet_list = RPCClient().get_packet_list()
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
            log_entries = RPCClient().get_log_entries()

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
