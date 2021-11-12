import logging
import shutil
import subprocess

from aprsd import plugin, trace


LOG = logging.getLogger("APRSD")


class FortunePlugin(plugin.APRSDRegexCommandPluginBase):
    """Fortune."""

    command_regex = "^[fF]"
    command_name = "fortune"
    short_description = "Give me a fortune"

    fortune_path = None

    def setup(self):
        self.fortune_path = shutil.which("fortune")
        if not self.fortune_path:
            self.enabled = False
        else:
            self.enabled = True

    @trace.trace
    def process(self, packet):
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
