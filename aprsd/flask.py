import datetime
import json
import logging
from logging import NullHandler
from logging.handlers import RotatingFileHandler
import sys
import time

from aprsd import client, messaging, plugin, stats, utils
from aprslib.exceptions import LoginError
import flask
from flask import request
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
        return flask.render_template(
            "index.html",
            initial_stats=stats,
            callsign=self.config["aprs"]["login"],
        )

    @auth.login_required
    def messages(self):
        track = messaging.MsgTrack()
        msgs = []
        for id in track:
            LOG.info(track[id].dict())
            msgs.append(track[id].dict())

        return flask.render_template("messages.html", messages=json.dumps(msgs))

    def setup_connection(self):
        user = self.config["aprs"]["login"]
        password = self.config["aprs"]["password"]
        host = self.config["aprs"].get("host", "rotate.aprs.net")
        port = self.config["aprs"].get("port", 14580)
        connected = False
        backoff = 1
        while not connected:
            try:
                LOG.info("Creating aprslib client")
                aprs_client = client.Aprsdis(
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
                LOG.error("Failed to login to APRS-IS Server '{}'".format(e))
                connected = False
                raise e
            except Exception as e:
                LOG.error("Unable to connect to APRS-IS server. '{}' ".format(e))
                time.sleep(backoff)
                backoff = backoff * 2
                continue
        LOG.debug("Logging in to APRS-IS with user '%s'" % user)
        return aprs_client

    def send_message(self):
        if request.method == "POST":
            from_call = request.form["from_call"]
            to_call = request.form["to_call"]
            message = request.form["message"]
            LOG.info(
                "From: '{}' To: '{}'  Send '{}'".format(
                    from_call,
                    to_call,
                    message,
                ),
            )

            try:
                aprsis_client = self.setup_connection()
            except LoginError as e:
                result = "Failed to setup Connection {}".format(e)

            msg = messaging.TextMessage(from_call, to_call, message)
            msg.send_direct(aprsis_client=aprsis_client)
            result = "Message sent"
        else:
            from_call = self.config["aprs"]["login"]
            result = ""

        return flask.render_template(
            "send-message.html",
            from_call=from_call,
            result=result,
        )

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
        static_url_path="",
        static_folder="web/static",
        template_folder="web/templates",
    )
    setup_logging(config, flask_app, loglevel, quiet)
    server = APRSDFlask()
    server.set_config(config)
    flask_app.route("/", methods=["GET"])(server.index)
    flask_app.route("/stats", methods=["GET"])(server.stats)
    flask_app.route("/messages", methods=["GET"])(server.messages)
    flask_app.route("/send-message", methods=["GET", "POST"])(server.send_message)
    flask_app.route("/save", methods=["GET"])(server.save)
    flask_app.route("/plugins", methods=["GET"])(server.plugins)
    return flask_app
