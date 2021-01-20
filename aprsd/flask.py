import datetime
import json

import aprsd
from aprsd import messaging
import flask
import flask_classful


class APRSDFlask(flask_classful.FlaskView):
    config = None

    def set_config(self, config):
        self.config = config

    def index(self):
        return "Hello"
        # return flask.render_template("index.html", message=msg)

    def stats(self):
        track = messaging.MsgTrack()
        uptime = datetime.datetime.now() - track._start_time
        stats = {
            "version": aprsd.__version__,
            "uptime": str(uptime),
            "size_tracker": len(track),
        }
        return json.dumps(stats)


def init_flask(config):
    flask_app = flask.Flask("aprsd")
    server = APRSDFlask()
    server.set_config(config)
    # flask_app.route('/', methods=['GET'])(server.index)
    flask_app.route("/stats", methods=["GET"])(server.stats)
    return flask_app
