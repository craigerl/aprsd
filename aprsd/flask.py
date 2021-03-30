import datetime
import json
import logging
import tracemalloc

import aprsd
from aprsd import client, messaging, plugin, stats
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
        return flask.render_template("index.html", initial_stats=stats)

    @auth.login_required
    def messages(self):
        track = messaging.MsgTrack()
        msgs = []
        for id in track:
            LOG.info(track[id].dict())
            msgs.append(track[id].dict())

        return flask.render_template("messages.html", messages=json.dumps(msgs))

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
        current, peak = tracemalloc.get_traced_memory()
        cl = client.Client()
        server_string = cl.client.server_string

        result = {
            "version": aprsd.__version__,
            "aprsis_server": server_string,
            "uptime": stats_obj.uptime,
            "size_tracker": len(track),
            "stats": stats_obj.stats(),
            "time": now.strftime("%m-%d-%Y %H:%M:%S"),
            "memory_current": current,
            "memory_peak": peak,
        }

        return result

    def stats(self):
        return json.dumps(self._stats())


def init_flask(config):
    flask_app = flask.Flask(
        "aprsd",
        static_url_path="",
        static_folder="web/static",
        template_folder="web/templates",
    )
    server = APRSDFlask()
    server.set_config(config)
    flask_app.route("/", methods=["GET"])(server.index)
    flask_app.route("/stats", methods=["GET"])(server.stats)
    flask_app.route("/messages", methods=["GET"])(server.messages)
    flask_app.route("/save", methods=["GET"])(server.save)
    flask_app.route("/plugins", methods=["GET"])(server.plugins)
    return flask_app
