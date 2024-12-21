from aprsd import plugin, threads
from aprsd.packets import core

FAKE_MESSAGE_TEXT = "fake MeSSage"
FAKE_FROM_CALLSIGN = "KFAKE"
FAKE_TO_CALLSIGN = "KMINE"


def fake_packet(
    fromcall=FAKE_FROM_CALLSIGN,
    tocall=FAKE_TO_CALLSIGN,
    message=None,
    msg_number=None,
    message_format=core.PACKET_TYPE_MESSAGE,
    response=None,
):
    packet_dict = {
        "from": fromcall,
        "addresse": tocall,
        "to": tocall,
        "format": message_format,
        "raw": "",
    }
    if message:
        packet_dict["message_text"] = message

    if msg_number:
        packet_dict["msgNo"] = str(msg_number)

    if response:
        packet_dict["response"] = response

    return core.factory(packet_dict)


def fake_ack_packet():
    return fake_packet(
        msg_number=12,
        response=core.PACKET_TYPE_ACK,
    )


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
        return False


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


class FakeWatchListPlugin(plugin.APRSDWatchListPluginBase):
    def process(self, packet):
        return FAKE_MESSAGE_TEXT
