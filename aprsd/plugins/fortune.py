import logging
import shutil
import subprocess

from aprsd import packets, plugin
from aprsd.utils import trace


LOG = logging.getLogger("APRSD")

DEFAULT_FORTUNE_PATH = '/usr/games/fortune'


class FortunePlugin(plugin.APRSDRegexCommandPluginBase):
    """Fortune."""

    command_regex = r"^([f]|[f]\s|fortune)"
    command_name = "fortune"
    short_description = "Give me a fortune"

    fortune_path = None

    def setup(self):
        self.fortune_path = shutil.which(DEFAULT_FORTUNE_PATH)
        LOG.info(f"Fortune path {self.fortune_path}")
        if not self.fortune_path:
            self.enabled = False
        else:
            self.enabled = True

    @trace.trace
    def process(self, packet: packets.MessagePacket):
        LOG.info("FortunePlugin")

        # fromcall = packet.get("from")
        # message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")

        reply = None

        try:
            cmnd = [self.fortune_path, "-s", "-n 60"]
            command = " ".join(cmnd)
            output = subprocess.check_output(
                command,
                shell=True,
                timeout=3,
                universal_newlines=True,
            )
            output = (
                output.replace("\r", "")
                .replace("\n", "")
                .replace("  ", "")
                .replace("\t", " ")
            )
        except subprocess.CalledProcessError as ex:
            reply = f"Fortune command failed '{ex.output}'"
        else:
            reply = output

        return reply
