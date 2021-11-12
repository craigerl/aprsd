import datetime
import json
import logging
from logging import NullHandler
from logging.handlers import RotatingFileHandler
import sys
import threading
import time

import aprslib
from aprslib.exceptions import LoginError
import flask
from flask import request
import flask_classful
from flask_httpauth import HTTPBasicAuth
from flask_socketio import Namespace, SocketIO
from werkzeug.security import check_password_hash, generate_password_hash

import aprsd
from aprsd import client
from aprsd import config as aprsd_config
from aprsd import log, messaging, packets, plugin, stats, threads, utils
from aprsd.clients import aprsis


LOG = logging.getLogger("APRSD")

auth = HTTPBasicAuth()
users = None


class SentMessages:
    _instance = None
    lock = None

    msgs = {}

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any initialization here.
            cls.lock = threading.Lock()
        return cls._instance

    def add(self, msg):
        with self.lock:
            self.msgs[msg.id] = self._create(msg.id)
            self.msgs[msg.id]["from"] = msg.fromcall
            self.msgs[msg.id]["to"] = msg.tocall
            self.msgs[msg.id]["message"] = msg.message.rstrip("\n")
            self.msgs[msg.id]["raw"] = str(msg).rstrip("\n")

    def _create(self, id):
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

    def __len__(self):
        with self.lock:
            return len(self.msgs.keys())

    def get(self, id):
        with self.lock:
            if id in self.msgs:
                return self.msgs[id]

    def get_all(self):
        with self.lock:
            return self.msgs

    def set_status(self, id, status):
        with self.lock:
            self.msgs[id]["last_update"] = str(datetime.datetime.now())
            self.msgs[id]["status"] = status

    def ack(self, id):
        """The message got an ack!"""
        with self.lock:
            self.msgs[id]["last_update"] = str(datetime.datetime.now())
            self.msgs[id]["ack"] = True

    def reply(self, id, packet):
        """We got a packet back from the sent message."""
        with self.lock:
            self.msgs[id]["reply"] = packet


# HTTPBasicAuth doesn't work on a class method.
# This has to be out here.  Rely on the APRSDFlask
# class to initialize the users from the config
@auth.verify_password
def verify_password(username, password):
    global users

    if username in users and check_password_hash(users.get(username), password):
        return username


class SendMessageThread(threads.APRSDThread):
    """Thread for sending a message from web."""

    aprsis_client = None
    request = None
    got_ack = False
    got_reply = False

    def __init__(self, config, info, msg, namespace):
        self.config = config
        self.request = info
        self.msg = msg
        self.namespace = namespace
        self.start_time = datetime.datetime.now()
        msg = "({} -> {}) : {}".format(
            info["from"],
            info["to"],
            info["message"],
        )
        super().__init__(f"WEB_SEND_MSG-{msg}")

    def setup_connection(self):
        user = self.request["from"]
        password = self.request["password"]
        host = self.config["aprs"].get("host", "rotate.aprs.net")
        port = self.config["aprs"].get("port", 14580)
        connected = False
        backoff = 1
        while not connected:
            try:
                LOG.info("Creating aprslib client")

                aprs_client = aprsis.Aprsdis(
                    user,
                    passwd=password,
                    host=host,
                    port=port,
                )
                # Force the logging to be the same
                aprs_client.logger = LOG
                aprs_client.connect()
                connected = True
                backoff = 1
            except LoginError as e:
                LOG.error(f"Failed to login to APRS-IS Server '{e}'")
                connected = False
                raise e
            except Exception as e:
                LOG.error(f"Unable to connect to APRS-IS server. '{e}' ")
                time.sleep(backoff)
                backoff = backoff * 2
                continue
        LOG.debug(f"Logging in to APRS-IS with user '{user}'")
        return aprs_client

    def run(self):
        LOG.debug("Starting")
        from_call = self.request["from"]
        to_call = self.request["to"]
        message = self.request["message"]
        LOG.info(
            "From: '{}' To: '{}'  Send '{}'".format(
                from_call,
                to_call,
                message,
            ),
        )

        try:
            self.aprs_client = self.setup_connection()
        except LoginError as e:
            f"Failed to setup Connection {e}"

        self.msg.send_direct(aprsis_client=self.aprs_client)
        SentMessages().set_status(self.msg.id, "Sent")

        while not self.thread_stop:
            can_loop = self.loop()
            if not can_loop:
                self.stop()
        threads.APRSDThreadList().remove(self)
        LOG.debug("Exiting")

    def rx_packet(self, packet):
        global socketio
        # LOG.debug("Got packet back {}".format(packet))
        resp = packet.get("response", None)
        if resp == "ack":
            ack_num = packet.get("msgNo")
            LOG.info(f"We got ack for our sent message {ack_num}")
            messaging.log_packet(packet)
            SentMessages().ack(self.msg.id)
            socketio.emit(
                "ack", SentMessages().get(self.msg.id),
                namespace="/sendmsg",
            )
            stats.APRSDStats().ack_rx_inc()
            self.got_ack = True
            if self.request["wait_reply"] == "0" or self.got_reply:
                # We aren't waiting for a reply, so we can bail
                self.stop()
                self.thread_stop = self.aprs_client.thread_stop = True
        else:
            packets.PacketList().add(packet)
            stats.APRSDStats().msgs_rx_inc()
            message = packet.get("message_text", None)
            fromcall = packet["from"]
            msg_number = packet.get("msgNo", "0")
            messaging.log_message(
                "Received Message",
                packet["raw"],
                message,
                fromcall=fromcall,
                ack=msg_number,
            )
            SentMessages().reply(self.msg.id, packet)
            SentMessages().set_status(self.msg.id, "Got Reply")
            socketio.emit(
                "reply", SentMessages().get(self.msg.id),
                namespace="/sendmsg",
            )

            # Send the ack back?
            ack = messaging.AckMessage(
                self.request["from"],
                fromcall,
                msg_id=msg_number,
            )
            ack.send_direct()
            SentMessages().set_status(self.msg.id, "Ack Sent")

            # Now we can exit, since we are done.
            self.got_reply = True
            if self.got_ack:
                self.stop()
                self.thread_stop = self.aprs_client.thread_stop = True

    def loop(self):
        # we have a general time limit expecting results of
        # around 120 seconds before we exit
        now = datetime.datetime.now()
        start_delta = str(now - self.start_time)
        delta = utils.parse_delta_str(start_delta)
        d = datetime.timedelta(**delta)
        max_timeout = {"hours": 0.0, "minutes": 1, "seconds": 0}
        max_delta = datetime.timedelta(**max_timeout)
        if d > max_delta:
            LOG.error("XXXXXX Haven't completed everything in 60 seconds.  BAIL!")
            return False

        if self.got_ack and self.got_reply:
            LOG.warning("We got everything already. BAIL")
            return False

        try:
            # This will register a packet consumer with aprslib
            # When new packets come in the consumer will process
            # the packet
            self.aprs_client.consumer(self.rx_packet, raw=False, blocking=False)
        except aprslib.exceptions.ConnectionDrop:
            LOG.error("Connection dropped.")
            return False

        return True


class APRSDFlask(flask_classful.FlaskView):
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

    @auth.login_required
    def index(self):
        stats = self._stats()
        LOG.debug(
            "watch list? {}".format(
                self.config["aprsd"]["watch_list"],
            ),
        )
        wl = packets.WatchList()
        if wl.is_enabled():
            watch_count = len(wl)
            watch_age = wl.max_delta()
        else:
            watch_count = 0
            watch_age = 0

        sl = packets.SeenList()
        seen_count = len(sl)

        pm = plugin.PluginManager()
        plugins = pm.get_plugins()
        plugin_count = len(plugins)

        if self.config["aprs"].get("enabled", True):
            transport = "aprs-is"
            aprs_connection = (
                "APRS-IS Server: <a href='http://status.aprs2.net' >"
                "{}</a>".format(stats["stats"]["aprs-is"]["server"])
            )
        else:
            # We might be connected to a KISS socket?
            if client.KISSClient.kiss_enabled(self.config):
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

        stats["transport"] = transport
        stats["aprs_connection"] = aprs_connection

        return flask.render_template(
            "index.html",
            initial_stats=stats,
            aprs_connection=aprs_connection,
            callsign=self.config["aprs"]["login"],
            version=aprsd.__version__,
            config_json=json.dumps(self.config.data),
            watch_count=watch_count,
            watch_age=watch_age,
            seen_count=seen_count,
            plugin_count=plugin_count,
        )

    @auth.login_required
    def messages(self):
        track = messaging.MsgTrack()
        msgs = []
        for id in track:
            LOG.info(track[id].dict())
            msgs.append(track[id].dict())

        return flask.render_template("messages.html", messages=json.dumps(msgs))

    @auth.login_required
    def send_message_status(self):
        LOG.debug(request)
        msgs = SentMessages()
        info = msgs.get_all()
        return json.dumps(info)

    @auth.login_required
    def send_message(self):
        LOG.debug(request)
        if request.method == "GET":
            return flask.render_template(
                "send-message.html",
                callsign=self.config["aprs"]["login"],
                version=aprsd.__version__,
            )

    @auth.login_required
    def packets(self):
        packet_list = packets.PacketList().get()
        return json.dumps(packet_list)

    @auth.login_required
    def plugins(self):
        pm = plugin.PluginManager()
        pm.reload_plugins()

        return "reloaded"

    @auth.login_required
    def save(self):
        """Save the existing queue to disk."""
        track = messaging.MsgTrack()
        track.save()
        return json.dumps({"messages": "saved"})

    def _stats(self):
        stats_obj = stats.APRSDStats()
        track = messaging.MsgTrack()
        now = datetime.datetime.now()

        time_format = "%m-%d-%Y %H:%M:%S"

        stats_dict = stats_obj.stats()

        # Convert the watch_list entries to age
        wl = packets.WatchList()
        new_list = {}
        for call in wl.get_all():
            # call_date = datetime.datetime.strptime(
            #    str(wl.last_seen(call)),
            #    "%Y-%m-%d %H:%M:%S.%f",
            # )
            new_list[call] = {
                "last": wl.age(call),
                "packets": wl.get(call)["packets"].get(),
            }

        stats_dict["aprsd"]["watch_list"] = new_list
        packet_list = packets.PacketList()
        rx = packet_list.total_received()
        tx = packet_list.total_sent()
        stats_dict["packets"] = {
            "sent": tx,
            "received": rx,
        }

        result = {
            "time": now.strftime(time_format),
            "size_tracker": len(track),
            "stats": stats_dict,
        }

        return result

    def stats(self):
        return json.dumps(self._stats())


class SendMessageNamespace(Namespace):
    _config = None
    got_ack = False
    reply_sent = False
    msg = None
    request = None

    def __init__(self, namespace=None, config=None):
        self._config = config
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
        msg = messaging.TextMessage(
            data["from"], data["to"],
            data["message"],
        )
        self.msg = msg
        msgs = SentMessages()
        msgs.add(msg)
        msgs.set_status(msg.id, "Sending")
        socketio.emit(
            "sent", SentMessages().get(self.msg.id),
            namespace="/sendmsg",
        )

        socketio.start_background_task(self._start, self._config, data, msg, self)
        LOG.warning("WS: on_send: exit")

    def _start(self, config, data, msg, namespace):
        msg_thread = SendMessageThread(self._config, data, msg, self)
        msg_thread.start()

    def handle_message(self, data):
        LOG.debug(f"WS Data {data}")

    def handle_json(self, data):
        LOG.debug(f"WS json {data}")


class LogMonitorThread(threads.APRSDThread):

    def __init__(self):
        super().__init__("LogMonitorThread")

    def loop(self):
        global socketio
        try:
            record = log.logging_queue.get(block=True, timeout=5)
            json_record = self.json_record(record)
            socketio.emit(
                "log_entry", json_record,
                namespace="/logs",
            )
        except Exception:
            # Just ignore thi
            pass

        return True

    def json_record(self, record):
        entry = {}
        entry["filename"] = record.filename
        entry["funcName"] = record.funcName
        entry["levelname"] = record.levelname
        entry["lineno"] = record.lineno
        entry["module"] = record.module
        entry["name"] = record.name
        entry["pathname"] = record.pathname
        entry["process"] = record.process
        entry["processName"] = record.processName
        if hasattr(record, "stack_info"):
            entry["stack_info"] = record.stack_info
        else:
            entry["stack_info"] = None
        entry["thread"] = record.thread
        entry["threadName"] = record.threadName
        entry["message"] = record.getMessage()
        return entry


class LoggingNamespace(Namespace):

    def on_connect(self):
        global socketio
        LOG.debug("Web socket connected")
        socketio.emit(
            "connected", {"data": "/logs Connected"},
            namespace="/logs",
        )
        self.log_thread = LogMonitorThread()
        self.log_thread.start()

    def on_disconnect(self):
        LOG.debug("WS Disconnected")
        self.log_thread.stop()


def setup_logging(config, flask_app, loglevel, quiet):
    flask_log = logging.getLogger("werkzeug")

    if not config["aprsd"]["web"].get("logging_enabled", False):
        # disable web logging
        flask_log.disabled = True
        flask_app.logger.disabled = True
        return

    log_level = aprsd_config.LOG_LEVELS[loglevel]
    LOG.setLevel(log_level)
    log_format = config["aprsd"].get("logformat", aprsd_config.DEFAULT_LOG_FORMAT)
    date_format = config["aprsd"].get("dateformat", aprsd_config.DEFAULT_DATE_FORMAT)
    log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    log_file = config["aprsd"].get("logfile", None)
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=(10248576 * 5), backupCount=4)
    else:
        fh = NullHandler()

    fh.setFormatter(log_formatter)
    for handler in flask_app.logger.handlers:
        handler.setFormatter(log_formatter)
        print(handler)

    flask_log.addHandler(fh)

    if not quiet:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        flask_log.addHandler(sh)


def init_flask(config, loglevel, quiet):
    global socketio

    flask_app = flask.Flask(
        "aprsd",
        static_url_path="/static",
        static_folder="web/static",
        template_folder="web/templates",
    )
    setup_logging(config, flask_app, loglevel, quiet)
    server = APRSDFlask()
    server.set_config(config)
    flask_app.route("/", methods=["GET"])(server.index)
    flask_app.route("/stats", methods=["GET"])(server.stats)
    flask_app.route("/messages", methods=["GET"])(server.messages)
    flask_app.route("/packets", methods=["GET"])(server.packets)
    flask_app.route("/send-message", methods=["GET"])(server.send_message)
    flask_app.route("/send-message-status", methods=["GET"])(server.send_message_status)
    flask_app.route("/save", methods=["GET"])(server.save)
    flask_app.route("/plugins", methods=["GET"])(server.plugins)

    socketio = SocketIO(
        flask_app, logger=False, engineio_logger=False,
        async_mode="threading",
    )
    #    import eventlet
    #    eventlet.monkey_patch()

    socketio.on_namespace(SendMessageNamespace("/sendmsg", config=config))
    socketio.on_namespace(LoggingNamespace("/logs"))
    return socketio, flask_app
