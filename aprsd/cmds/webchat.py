import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import queue
import signal
import sys
import threading
import time

import aprslib
from aprslib import util as aprslib_util
import click
from device_detector import DeviceDetector
import flask
from flask import request
from flask.logging import default_handler
import flask_classful
from flask_httpauth import HTTPBasicAuth
from flask_socketio import Namespace, SocketIO
from werkzeug.security import check_password_hash, generate_password_hash
import wrapt

import aprsd
from aprsd import cli_helper, client
from aprsd import config as aprsd_config
from aprsd import messaging, packets, stats, threads, utils
from aprsd.aprsd import cli
from aprsd.logging import rich as aprsd_logging
from aprsd.threads import aprsd as aprsd_thread
from aprsd.threads import rx
from aprsd.utils import objectstore, trace


LOG = logging.getLogger("APRSD")
auth = HTTPBasicAuth()
users = None
rx_msg_queue = queue.Queue(maxsize=20)
tx_msg_queue = queue.Queue(maxsize=20)
control_queue = queue.Queue(maxsize=20)
msg_queues = {
    "rx": rx_msg_queue,
    "control": control_queue,
    "tx": tx_msg_queue,
}


def signal_handler(sig, frame):

    click.echo("signal_handler: called")
    LOG.info(
        f"Ctrl+C, Sending all threads({len(threads.APRSDThreadList())}) exit! "
        f"Can take up to 10 seconds {datetime.datetime.now()}",
    )
    threads.APRSDThreadList().stop_all()
    if "subprocess" not in str(frame):
        time.sleep(1.5)
        # messaging.MsgTrack().save()
        # packets.WatchList().save()
        # packets.SeenList().save()
        LOG.info(stats.APRSDStats())
        LOG.info("Telling flask to bail.")
        signal.signal(signal.SIGTERM, sys.exit(0))
        sys.exit(0)


class SentMessages(objectstore.ObjectStoreMixin):
    _instance = None
    lock = threading.Lock()

    data = {}

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @wrapt.synchronized(lock)
    def add(self, msg):
        self.data[msg.id] = self.create(msg.id)
        self.data[msg.id]["from"] = msg.fromcall
        self.data[msg.id]["to"] = msg.tocall
        self.data[msg.id]["message"] = msg.message.rstrip("\n")
        self.data[msg.id]["raw"] = str(msg).rstrip("\n")

    def create(self, id):
        return {
            "id": id,
            "ts": time.time(),
            "ack": False,
            "from": None,
            "to": None,
            "raw": None,
            "message": None,
            "status": None,
            "last_update": None,
            "reply": None,
        }

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

    if username in users and check_password_hash(users.get(username), password):
        return username


class WebChatRXThread(rx.APRSDRXThread):
    """Class that connects to aprsis/kiss and waits for messages."""

    def connected(self, connected=True):
        self.connected = connected

    def stop(self):
        self.thread_stop = True
        client.factory.create().client.stop()

    def loop(self):
        # setup the consumer of messages and block until a messages
        msg = None
        try:
            msg = self.msg_queues["tx"].get_nowait()
        except queue.Empty:
            pass

        try:
            if msg:
                LOG.debug("GOT msg from TX queue!!")
                msg.send()
        except (
            aprslib.exceptions.ConnectionDrop,
            aprslib.exceptions.ConnectionError,
        ):
            LOG.error("Connection dropped, reconnecting")
            # Put it back on the queue to send.
            self.msg_queues["tx"].put(msg)
            # Force the deletion of the client object connected to aprs
            # This will cause a reconnect, next time client.get_client()
            # is called
            self._client.reset()
            time.sleep(2)

        try:
            # When new packets come in the consumer will process
            # the packet

            # This call blocks until thread stop() is called.
            self._client.client.consumer(
                self.process_packet, raw=False, blocking=False,
            )

        except (
            aprslib.exceptions.ConnectionDrop,
            aprslib.exceptions.ConnectionError,
        ):
            LOG.error("Connection dropped, reconnecting")
            time.sleep(5)
            # Force the deletion of the client object connected to aprs
            # This will cause a reconnect, next time client.get_client()
            # is called
            self._client.reset()
            return True
        return True

    def process_packet(self, *args, **kwargs):
        # packet = self._client.decode_packet(*args, **kwargs)
        if "packet" in kwargs:
            packet = kwargs["packet"]
        else:
            packet = self._client.decode_packet(*args, **kwargs)

        LOG.debug(f"GOT Packet {packet}")
        self.msg_queues["rx"].put(packet)


class WebChatTXThread(aprsd_thread.APRSDThread):
    """Class that """
    def __init__(self, msg_queues, config, socketio):
        super().__init__("_TXThread_")
        self.msg_queues = msg_queues
        self.config = config
        self.socketio = socketio
        self.connected = False

    def loop(self):
        try:
            msg = self.msg_queues["control"].get_nowait()
            self.connected = msg["connected"]
        except queue.Empty:
            pass
        try:
            packet = self.msg_queues["rx"].get_nowait()
            if packet:
                # we got a packet and we need to send it to the
                # web socket
                self.process_packet(packet)
        except queue.Empty:
            pass
        except Exception as ex:
            LOG.exception(ex)
        time.sleep(1)

        return True

    def process_ack_packet(self, packet):
        ack_num = packet.get("msgNo")
        LOG.info(f"We got ack for our sent message {ack_num}")
        messaging.log_packet(packet)
        SentMessages().ack(int(ack_num))
        self.socketio.emit(
            "ack", SentMessages().get(int(ack_num)),
            namespace="/sendmsg",
        )
        stats.APRSDStats().ack_rx_inc()
        self.got_ack = True

    def process_packet(self, packet):
        LOG.info(f"process PACKET {packet}")
        tocall = packet.get("addresse", None)
        fromcall = packet["from"]
        msg = packet.get("message_text", None)
        msg_id = packet.get("msgNo", "0")
        msg_response = packet.get("response", None)

        if (
            tocall.lower() == self.config["aprsd"]["callsign"].lower()
            and msg_response == "ack"
        ):
            self.process_ack_packet(packet)
        elif tocall.lower() == self.config["aprsd"]["callsign"].lower():
            messaging.log_message(
                "Received Message",
                packet["raw"],
                msg,
                fromcall=fromcall,
                msg_num=msg_id,
            )
            # let any threads do their thing, then ack
            # send an ack last
            ack = messaging.AckMessage(
                self.config["aprsd"]["callsign"],
                fromcall,
                msg_id=msg_id,
            )
            ack.send()

            packets.PacketList().add(packet)
            stats.APRSDStats().msgs_rx_inc()
            message = packet.get("message_text", None)
            msg = {
                "id": 0,
                "ts": time.time(),
                "ack": False,
                "from": fromcall,
                "to": packet["to"],
                "raw": packet["raw"],
                "message": message,
                "status": None,
                "last_update": None,
                "reply": None,
            }
            self.socketio.emit(
                "new", msg,
                namespace="/sendmsg",
            )


class WebChatFlask(flask_classful.FlaskView):
    config = None

    def set_config(self, config):
        global users
        self.config = config
        self.users = {}
        for user in self.config["aprsd"]["web"]["users"]:
            self.users[user] = generate_password_hash(
                self.config["aprsd"]["web"]["users"][user],
            )

        users = self.users

    def _get_transport(self, stats):
        if self.config["aprs"].get("enabled", True):
            transport = "aprs-is"
            aprs_connection = (
                "APRS-IS Server: <a href='http://status.aprs2.net' >"
                "{}</a>".format(stats["stats"]["aprs-is"]["server"])
            )
        else:
            # We might be connected to a KISS socket?
            if client.KISSClient.is_enabled(self.config):
                transport = client.KISSClient.transport(self.config)
                if transport == client.TRANSPORT_TCPKISS:
                    aprs_connection = (
                        "TCPKISS://{}:{}".format(
                            self.config["kiss"]["tcp"]["host"],
                            self.config["kiss"]["tcp"]["port"],
                        )
                    )
                elif transport == client.TRANSPORT_SERIALKISS:
                    aprs_connection = (
                        "SerialKISS://{}@{} baud".format(
                            self.config["kiss"]["serial"]["device"],
                            self.config["kiss"]["serial"]["baudrate"],
                        )
                    )

        return transport, aprs_connection

    @auth.login_required
    def index(self):
        user_agent = request.headers.get("User-Agent")
        device = DeviceDetector(user_agent).parse()
        LOG.debug(f"Device type {device.device_type()}")
        LOG.debug(f"Is mobile? {device.is_mobile()}")
        stats = self._stats()

        if device.is_mobile():
            html_template = "mobile.html"
        else:
            html_template = "index.html"

        # For development
        html_template = "mobile.html"

        LOG.debug(f"Template {html_template}")

        transport, aprs_connection = self._get_transport(stats)
        LOG.debug(f"transport {transport} aprs_connection {aprs_connection}")

        stats["transport"] = transport
        stats["aprs_connection"] = aprs_connection
        LOG.debug(f"initial stats = {stats}")

        return flask.render_template(
            html_template,
            initial_stats=stats,
            aprs_connection=aprs_connection,
            callsign=self.config["aprsd"]["callsign"],
            version=aprsd.__version__,
        )

    @auth.login_required
    def send_message_status(self):
        LOG.debug(request)
        msgs = SentMessages()
        info = msgs.get_all()
        return json.dumps(info)

    def _stats(self):
        stats_obj = stats.APRSDStats()
        now = datetime.datetime.now()

        time_format = "%m-%d-%Y %H:%M:%S"
        stats_dict = stats_obj.stats()
        # Webchat doesnt need these
        del stats_dict["aprsd"]["watch_list"]
        del stats_dict["aprsd"]["seen_list"]
        # del stats_dict["email"]
        # del stats_dict["plugins"]
        # del stats_dict["messages"]

        result = {
            "time": now.strftime(time_format),
            "stats": stats_dict,
        }

        return result

    def stats(self):
        return json.dumps(self._stats())


class SendMessageNamespace(Namespace):
    """Class to handle the socketio interactions."""
    _config = None
    got_ack = False
    reply_sent = False
    msg = None
    request = None

    def __init__(self, namespace=None, config=None, msg_queues=None):
        self._config = config
        self._msg_queues = msg_queues
        super().__init__(namespace)

    def on_connect(self):
        global socketio
        LOG.debug("Web socket connected")
        socketio.emit(
            "connected", {"data": "/sendmsg Connected"},
            namespace="/sendmsg",
        )
        msg = {"connected": True}
        self._msg_queues["control"].put(msg)

    def on_disconnect(self):
        LOG.debug("WS Disconnected")
        msg = {"connected": False}
        self._msg_queues["control"].put(msg)

    def on_send(self, data):
        global socketio
        LOG.debug(f"WS: on_send {data}")
        self.request = data
        data["from"] = self._config["aprs"]["login"]
        msg = messaging.TextMessage(
            data["from"],
            data["to"].upper(),
            data["message"],
        )
        self.msg = msg
        msgs = SentMessages()
        msgs.add(msg)
        msgs.set_status(msg.id, "Sending")
        obj = msgs.get(self.msg.id)
        socketio.emit(
            "sent", obj,
            namespace="/sendmsg",
        )
        msg.send()
        # self._msg_queues["tx"].put(msg)

    def on_gps(self, data):
        LOG.debug(f"WS on_GPS: {data}")
        lat = aprslib_util.latitude_to_ddm(data["latitude"])
        long = aprslib_util.longitude_to_ddm(data["longitude"])
        LOG.debug(f"Lat DDM {lat}")
        LOG.debug(f"Long DDM {long}")

        local_datetime = datetime.datetime.now()
        utc_offset_timedelta = datetime.datetime.utcnow() - local_datetime
        result_utc_datetime = local_datetime + utc_offset_timedelta
        time_zulu = result_utc_datetime.strftime("%d%H%M")

        # now construct a beacon to send over the client connection
        txt = (
            f"{self._config['aprs']['login']}>APZ100,WIDE2-1"
            f":!{lat}{long}#PHG7260 APRSD WebChat Beacon"
        )

        txt = f"@{time_zulu}z{lat}1{long}$APRSD WebChat Beacon"

        LOG.debug(f"Sending {txt}")
        beacon_msg = messaging.RawMessage(txt)
        beacon_msg.fromcall = self._config["aprs"]["login"]
        beacon_msg.tocall = "APDW16"
        beacon_msg.send_direct()

    def handle_message(self, data):
        LOG.debug(f"WS Data {data}")

    def handle_json(self, data):
        LOG.debug(f"WS json {data}")


def setup_logging(config, flask_app, loglevel, quiet):
    flask_log = logging.getLogger("werkzeug")
    flask_app.logger.removeHandler(default_handler)
    flask_log.removeHandler(default_handler)

    log_level = aprsd_config.LOG_LEVELS[loglevel]
    flask_log.setLevel(log_level)
    date_format = config["aprsd"].get(
        "dateformat",
        aprsd_config.DEFAULT_DATE_FORMAT,
    )

    if not config["aprsd"]["web"].get("logging_enabled", False):
        # disable web logging
        flask_log.disabled = True
        flask_app.logger.disabled = True
        # return

    if config["aprsd"].get("rich_logging", False) and not quiet:
        log_format = "%(message)s"
        log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
        rh = aprsd_logging.APRSDRichHandler(
            show_thread=True, thread_width=15,
            rich_tracebacks=True, omit_repeated_times=False,
        )
        rh.setFormatter(log_formatter)
        flask_log.addHandler(rh)

    log_file = config["aprsd"].get("logfile", None)

    if log_file:
        log_format = config["aprsd"].get(
            "logformat",
            aprsd_config.DEFAULT_LOG_FORMAT,
        )
        log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
        fh = RotatingFileHandler(
            log_file, maxBytes=(10248576 * 5),
            backupCount=4,
        )
        fh.setFormatter(log_formatter)
        flask_log.addHandler(fh)


@trace.trace
def init_flask(config, loglevel, quiet):
    global socketio

    flask_app = flask.Flask(
        "aprsd",
        static_url_path="/static",
        static_folder="web/chat/static",
        template_folder="web/chat/templates",
    )
    setup_logging(config, flask_app, loglevel, quiet)
    server = WebChatFlask()
    server.set_config(config)
    flask_app.route("/", methods=["GET"])(server.index)
    flask_app.route("/stats", methods=["GET"])(server.stats)
    # flask_app.route("/send-message", methods=["GET"])(server.send_message)
    flask_app.route("/send-message-status", methods=["GET"])(server.send_message_status)

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
            "/sendmsg", config=config,
            msg_queues=msg_queues,
        ),
    )
    return socketio, flask_app


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
    default=80,
    help="Port to listen to web requests",
)
@click.pass_context
@cli_helper.process_standard_options
def webchat(ctx, flush, port):
    """Web based HAM Radio chat program!"""
    ctx.obj["config_file"]
    loglevel = ctx.obj["loglevel"]
    quiet = ctx.obj["quiet"]
    config = ctx.obj["config"]

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if not quiet:
        click.echo("Load config")

    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)
    LOG.info(f"APRSD Started version: {aprsd.__version__}")

    flat_config = utils.flatten_dict(config)
    LOG.info("Using CONFIG values:")
    for x in flat_config:
        if "password" in x or "aprsd.web.users.admin" in x:
            LOG.info(f"{x} = XXXXXXXXXXXXXXXXXXX")
        else:
            LOG.info(f"{x} = {flat_config[x]}")

    stats.APRSDStats(config)

    # Initialize the client factory and create
    # The correct client object ready for use
    client.ClientFactory.setup(config)
    # Make sure we have 1 client transport enabled
    if not client.factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    if not client.factory.is_client_configured():
        LOG.error("APRS client is not properly configured in config file.")
        sys.exit(-1)

    packets.PacketList(config=config)
    messaging.MsgTrack(config=config)
    packets.WatchList(config=config)
    packets.SeenList(config=config)

    (socketio, app) = init_flask(config, loglevel, quiet)
    rx_thread = WebChatRXThread(
        msg_queues=msg_queues,
        config=config,
    )
    LOG.info("Start RX Thread")
    rx_thread.start()
    tx_thread = WebChatTXThread(
        msg_queues=msg_queues,
        config=config,
        socketio=socketio,
    )
    LOG.info("Start TX Thread")
    tx_thread.start()

    keepalive = threads.KeepAliveThread(config=config)
    LOG.info("Start KeepAliveThread")
    keepalive.start()
    LOG.info("Start socketio.run()")
    socketio.run(
        app,
        host=config["aprsd"]["web"]["host"],
        port=port,
    )

    LOG.info("WebChat exiting!!!!  Bye.")
