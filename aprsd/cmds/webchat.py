import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import signal
import sys
import threading
import time

from aprslib import util as aprslib_util
import click
import flask
from flask import request
from flask.logging import default_handler
from flask_httpauth import HTTPBasicAuth
from flask_socketio import Namespace, SocketIO
from oslo_config import cfg
from werkzeug.security import check_password_hash, generate_password_hash
import wrapt

import aprsd
from aprsd import cli_helper, client, conf, packets, stats, threads, utils
from aprsd.log import rich as aprsd_logging
from aprsd.main import cli
from aprsd.threads import rx, tx
from aprsd.utils import trace


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")
auth = HTTPBasicAuth()
users = {}
socketio = None

flask_app = flask.Flask(
    "aprsd",
    static_url_path="/static",
    static_folder="web/chat/static",
    template_folder="web/chat/templates",
)


def signal_handler(sig, frame):

    click.echo("signal_handler: called")
    LOG.info(
        f"Ctrl+C, Sending all threads({len(threads.APRSDThreadList())}) exit! "
        f"Can take up to 10 seconds {datetime.datetime.now()}",
    )
    threads.APRSDThreadList().stop_all()
    if "subprocess" not in str(frame):
        time.sleep(1.5)
        # packets.WatchList().save()
        # packets.SeenList().save()
        LOG.info(stats.APRSDStats())
        LOG.info("Telling flask to bail.")
        signal.signal(signal.SIGTERM, sys.exit(0))


class SentMessages:

    _instance = None
    lock = threading.Lock()

    data = {}

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def is_initialized(self):
        return True

    @wrapt.synchronized(lock)
    def add(self, msg):
        self.data[msg.msgNo] = msg.__dict__

    @wrapt.synchronized(lock)
    def __len__(self):
        return len(self.data.keys())

    @wrapt.synchronized(lock)
    def get(self, id):
        if id in self.data:
            return self.data[id]

    @wrapt.synchronized(lock)
    def get_all(self):
        return self.data

    @wrapt.synchronized(lock)
    def set_status(self, id, status):
        if id in self.data:
            self.data[id]["last_update"] = str(datetime.datetime.now())
            self.data[id]["status"] = status

    @wrapt.synchronized(lock)
    def ack(self, id):
        """The message got an ack!"""
        if id in self.data:
            self.data[id]["last_update"] = str(datetime.datetime.now())
            self.data[id]["ack"] = True

    @wrapt.synchronized(lock)
    def reply(self, id, packet):
        """We got a packet back from the sent message."""
        if id in self.data:
            self.data[id]["reply"] = packet


# HTTPBasicAuth doesn't work on a class method.
# This has to be out here.  Rely on the APRSDFlask
# class to initialize the users from the config
@auth.verify_password
def verify_password(username, password):
    global users

    if username in users and check_password_hash(users[username], password):
        return username


class WebChatProcessPacketThread(rx.APRSDProcessPacketThread):
    """Class that handles packets being sent to us."""
    def __init__(self, packet_queue, socketio):
        self.socketio = socketio
        self.connected = False
        super().__init__(packet_queue)

    def process_ack_packet(self, packet: packets.AckPacket):
        super().process_ack_packet(packet)
        ack_num = packet.get("msgNo")
        SentMessages().ack(ack_num)
        self.socketio.emit(
            "ack", SentMessages().get(ack_num),
            namespace="/sendmsg",
        )
        self.got_ack = True

    def process_our_message_packet(self, packet: packets.MessagePacket):
        LOG.info(f"process MessagePacket {repr(packet)}")
        self.socketio.emit(
            "new", packet.__dict__,
            namespace="/sendmsg",
        )


def set_config():
    global users


def _get_transport(stats):
    if CONF.aprs_network.enabled:
        transport = "aprs-is"
        aprs_connection = (
            "APRS-IS Server: <a href='http://status.aprs2.net' >"
            "{}</a>".format(stats["stats"]["aprs-is"]["server"])
        )
    elif client.KISSClient.is_enabled():
        transport = client.KISSClient.transport()
        if transport == client.TRANSPORT_TCPKISS:
            aprs_connection = (
                "TCPKISS://{}:{}".format(
                    CONF.kiss_tcp.host,
                    CONF.kiss_tcp.port,
                )
            )
        elif transport == client.TRANSPORT_SERIALKISS:
            # for pep8 violation
            aprs_connection = (
                "SerialKISS://{}@{} baud".format(
                    CONF.kiss_serial.device,
                    CONF.kiss_serial.baudrate,
                ),
            )
    elif CONF.fake_client.enabled:
        transport = client.TRANSPORT_FAKE
        aprs_connection = "Fake Client"

    return transport, aprs_connection


@auth.login_required
@flask_app.route("/")
def index():
    stats = _stats()

    # For development
    html_template = "index.html"
    LOG.debug(f"Template {html_template}")

    transport, aprs_connection = _get_transport(stats)
    LOG.debug(f"transport {transport} aprs_connection {aprs_connection}")

    stats["transport"] = transport
    stats["aprs_connection"] = aprs_connection
    LOG.debug(f"initial stats = {stats}")
    latitude = CONF.webchat.latitude
    if latitude:
        latitude = float(CONF.webchat.latitude)

    longitude = CONF.webchat.longitude
    if longitude:
        longitude = float(longitude)

    return flask.render_template(
        html_template,
        initial_stats=stats,
        aprs_connection=aprs_connection,
        callsign=CONF.callsign,
        version=aprsd.__version__,
        latitude=latitude,
        longitude=longitude,
    )


@auth.login_required
@flask_app.route("//send-message-status")
def send_message_status():
    LOG.debug(request)
    msgs = SentMessages()
    info = msgs.get_all()
    return json.dumps(info)


def _stats():
    stats_obj = stats.APRSDStats()
    now = datetime.datetime.now()

    time_format = "%m-%d-%Y %H:%M:%S"
    stats_dict = stats_obj.stats()
    # Webchat doesnt need these
    if "watch_list" in stats_dict["aprsd"]:
        del stats_dict["aprsd"]["watch_list"]
    if "seen_list" in stats_dict["aprsd"]:
        del stats_dict["aprsd"]["seen_list"]
    if "threads" in stats_dict["aprsd"]:
        del stats_dict["aprsd"]["threads"]
    # del stats_dict["email"]
    # del stats_dict["plugins"]
    # del stats_dict["messages"]

    result = {
        "time": now.strftime(time_format),
        "stats": stats_dict,
    }

    return result


@flask_app.route("/stats")
def get_stats():
    return json.dumps(_stats())


class SendMessageNamespace(Namespace):
    """Class to handle the socketio interactions."""
    got_ack = False
    reply_sent = False
    msg = None
    request = None

    def __init__(self, namespace=None, config=None):
        super().__init__(namespace)

    def on_connect(self):
        global socketio
        LOG.debug("Web socket connected")
        socketio.emit(
            "connected", {"data": "/sendmsg Connected"},
            namespace="/sendmsg",
        )

    def on_disconnect(self):
        LOG.debug("WS Disconnected")

    def on_send(self, data):
        global socketio
        LOG.debug(f"WS: on_send {data}")
        self.request = data
        data["from"] = CONF.callsign
        path = data.get("path", None)
        if not path:
            path = []
        elif "," in path:
            path_opts = path.split(",")
            path = [x.strip() for x in path_opts]
        else:
            path = [path]

        pkt = packets.MessagePacket(
            from_call=data["from"],
            to_call=data["to"].upper(),
            message_text=data["message"],
            path=path,
        )
        pkt.prepare()
        self.msg = pkt
        msgs = SentMessages()
        msgs.add(pkt)
        tx.send(pkt)
        msgs.set_status(pkt.msgNo, "Sending")
        obj = msgs.get(pkt.msgNo)
        socketio.emit(
            "sent", obj,
            namespace="/sendmsg",
        )

    def on_gps(self, data):
        LOG.debug(f"WS on_GPS: {data}")
        lat = aprslib_util.latitude_to_ddm(data["latitude"])
        long = aprslib_util.longitude_to_ddm(data["longitude"])
        LOG.debug(f"Lat DDM {lat}")
        LOG.debug(f"Long DDM {long}")

        tx.send(
            packets.GPSPacket(
                from_call=CONF.callsign,
                to_call="APDW16",
                latitude=lat,
                longitude=long,
                comment="APRSD WebChat Beacon",
            ),
            direct=True,
        )

    def handle_message(self, data):
        LOG.debug(f"WS Data {data}")

    def handle_json(self, data):
        LOG.debug(f"WS json {data}")


def setup_logging(flask_app, loglevel, quiet):
    flask_log = logging.getLogger("werkzeug")
    flask_app.logger.removeHandler(default_handler)
    flask_log.removeHandler(default_handler)

    log_level = conf.log.LOG_LEVELS[loglevel]
    flask_log.setLevel(log_level)
    date_format = CONF.logging.date_format

    if CONF.logging.rich_logging and not quiet:
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


@trace.trace
def init_flask(loglevel, quiet):
    global socketio, flask_app

    setup_logging(flask_app, loglevel, quiet)

    socketio = SocketIO(
        flask_app, logger=False, engineio_logger=False,
        async_mode="threading",
    )
    # async_mode="gevent",
    # async_mode="eventlet",
    #    import eventlet
    #    eventlet.monkey_patch()

    socketio.on_namespace(
        SendMessageNamespace(
            "/sendmsg",
        ),
    )
    return socketio


# main() ###
@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    "-f",
    "--flush",
    "flush",
    is_flag=True,
    show_default=True,
    default=False,
    help="Flush out all old aged messages on disk.",
)
@click.option(
    "-p",
    "--port",
    "port",
    show_default=True,
    default=None,
    help="Port to listen to web requests.  This overrides the config.webchat.web_port setting.",
)
@click.pass_context
@cli_helper.process_standard_options
def webchat(ctx, flush, port):
    """Web based HAM Radio chat program!"""
    loglevel = ctx.obj["loglevel"]
    quiet = ctx.obj["quiet"]

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)
    LOG.info(f"APRSD Started version: {aprsd.__version__}")

    CONF.log_opt_values(LOG, logging.DEBUG)
    user = CONF.admin.user
    users[user] = generate_password_hash(CONF.admin.password)
    if not port:
        port = CONF.webchat.web_port

    # Initialize the client factory and create
    # The correct client object ready for use
    client.ClientFactory.setup()
    # Make sure we have 1 client transport enabled
    if not client.factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    if not client.factory.is_client_configured():
        LOG.error("APRS client is not properly configured in config file.")
        sys.exit(-1)

    packets.PacketList()
    packets.PacketTrack()
    packets.WatchList()
    packets.SeenList()

    keepalive = threads.KeepAliveThread()
    LOG.info("Start KeepAliveThread")
    keepalive.start()

    socketio = init_flask(loglevel, quiet)
    rx_thread = rx.APRSDPluginRXThread(
        packet_queue=threads.packet_queue,
    )
    rx_thread.start()
    process_thread = WebChatProcessPacketThread(
        packet_queue=threads.packet_queue,
        socketio=socketio,
    )
    process_thread.start()

    LOG.info("Start socketio.run()")
    socketio.run(
        flask_app,
        # This is broken for now after removing cryptography
        # and pyopenssl
        # ssl_context="adhoc",
        host=CONF.webchat.web_ip,
        port=port,
        allow_unsafe_werkzeug=True,
    )

    LOG.info("WebChat exiting!!!!  Bye.")
