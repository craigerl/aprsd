from aprsd import packets, plugin, threads


FAKE_MESSAGE_TEXT = "fake MeSSage"
FAKE_FROM_CALLSIGN = "KFART"
FAKE_TO_CALLSIGN = "KMINE"


def fake_packet(
    fromcall=FAKE_FROM_CALLSIGN,
    tocall=FAKE_TO_CALLSIGN,
    message=None,
    msg_number=None,
    message_format=packets.PACKET_TYPE_MESSAGE,
):
    packet = {
        "from": fromcall,
        "addresse": tocall,
        "format": message_format,
    }
    if message:
        packet["message_text"] = message

    if msg_number:
        packet["msgNo"] = msg_number

    return packet


class FakeBaseNoThreadsPlugin(plugin.APRSDPluginBase):
    version = "1.0"

    def setup(self):
        self.enabled = True

    def filter(self, packet):
        return None

    def process(self, packet):
        return "process"


class FakeThread(threads.APRSDThread):
    def __init__(self):
        super().__init__("FakeThread")

    def loop(self):
        return True


class FakeBaseThreadsPlugin(plugin.APRSDPluginBase):
    version = "1.0"

    def setup(self):
        self.enabled = True

    def filter(self, packet):
        return None

    def process(self, packet):
        return "process"

    def create_threads(self):
        return FakeThread()


class FakeRegexCommandPlugin(plugin.APRSDRegexCommandPluginBase):
    version = "1.0"
    command_regex = "^[fF]"
    command_name = "fake"

    def process(self, packet):
        return FAKE_MESSAGE_TEXT
