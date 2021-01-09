import logging
import shutil
import subprocess

from aprsd import plugin

LOG = logging.getLogger("APRSD")


class FortunePlugin(plugin.APRSDPluginBase):
    """Fortune."""

    version = "1.0"
    command_regex = "^[fF]"
    command_name = "fortune"

    def command(self, fromcall, message, ack):
        LOG.info("FortunePlugin")
        reply = None

        fortune_path = shutil.which("fortune")
        if not fortune_path:
            reply = "Fortune command not installed"
            return reply

        try:
            process = subprocess.Popen(
                [fortune_path, "-s", "-n 60"],
                stdout=subprocess.PIPE,
            )
            reply = process.communicate()[0]
            reply = reply.decode(errors="ignore").rstrip()
        except Exception as ex:
            reply = "Fortune command failed '{}'".format(ex)
            LOG.error(reply)

        return reply
