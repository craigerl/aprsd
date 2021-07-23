import datetime
import json
import logging
from logging import NullHandler
from logging.handlers import RotatingFileHandler
import sys

import aprsd
from aprsd import messaging, packets, plugin, stats, utils
import flask
import flask_classful
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash

LOG = logging.getLogger("APRSD")

auth = HTTPBasicAuth()
users = None


# HTTPBasicAuth doesn't work on a class method.
# This has to be out here.  Rely on the APRSDFlask
# class to initialize the users from the config
@auth.verify_password
def verify_password(username, password):
    global users

    if username in users and check_password_hash(users.get(username), password):
        return username


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
            watch_count = len(wl.callsigns)
            watch_age = wl.max_delta()
        else:
            watch_count = 0
            watch_age = 0

        return flask.render_template(
            "index.html",
            initial_stats=stats,
            callsign=self.config["aprs"]["login"],
            version=aprsd.__version__,
            config_json=json.dumps(self.config),
            watch_count=watch_count,
            watch_age=watch_age,
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
        for call in wl.callsigns:
            # call_date = datetime.datetime.strptime(
            #    str(wl.last_seen(call)),
            #    "%Y-%m-%d %H:%M:%S.%f",
            # )
            new_list[call] = {
                "last": wl.age(call),
                "packets": wl.callsigns[call]["packets"].get(),
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


def setup_logging(config, flask_app, loglevel, quiet):
    flask_log = logging.getLogger("werkzeug")

    if not config["aprsd"]["web"].get("logging_enabled", False):
        # disable web logging
        flask_log.disabled = True
        flask_app.logger.disabled = True
        return

    log_level = utils.LOG_LEVELS[loglevel]
    LOG.setLevel(log_level)
    log_format = config["aprsd"].get("logformat", utils.DEFAULT_LOG_FORMAT)
    date_format = config["aprsd"].get("dateformat", utils.DEFAULT_DATE_FORMAT)
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
    flask_app.route("/save", methods=["GET"])(server.save)
    flask_app.route("/plugins", methods=["GET"])(server.plugins)
    return flask_app
