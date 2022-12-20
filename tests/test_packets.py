import unittest

from aprsd import packets
from aprsd.packets import core

from . import fake


class TestPluginBase(unittest.TestCase):

    def _fake_dict(
        self,
        from_call=fake.FAKE_FROM_CALLSIGN,
        to_call=fake.FAKE_TO_CALLSIGN,
        message=None,
        msg_number=None,
        message_format=core.PACKET_TYPE_MESSAGE,
    ):
        packet_dict = {
            "from": from_call,
            "addresse": to_call,
            "to": to_call,
            "format": message_format,
            "raw": "",
        }

        if message:
            packet_dict["message_text"] = message

        if msg_number:
            packet_dict["msgNo"] = str(msg_number)

        return packet_dict

    def test_packet_construct(self):
        pkt = packets.Packet(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
        )

        self.assertEqual(fake.FAKE_FROM_CALLSIGN, pkt.from_call)
        self.assertEqual(fake.FAKE_TO_CALLSIGN, pkt.to_call)

    def test_packet_get_attr(self):
        pkt = packets.Packet(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
        )

        self.assertEqual(
            fake.FAKE_FROM_CALLSIGN,
            pkt.get("from_call"),
        )

    def test_packet_factory(self):
        pkt_dict = self._fake_dict()
        pkt = packets.Packet.factory(pkt_dict)

        self.assertIsInstance(pkt, packets.MessagePacket)
        self.assertEqual(fake.FAKE_FROM_CALLSIGN, pkt.from_call)
        self.assertEqual(fake.FAKE_TO_CALLSIGN, pkt.to_call)
        self.assertEqual(fake.FAKE_TO_CALLSIGN, pkt.addresse)

        pkt_dict["symbol"] = "_"
        pkt_dict["weather"] = {
            "wind_gust": 1.11,
            "temperature": 32.01,
            "humidity": 85,
            "pressure": 1095.12,
            "comment": "Home!",
        }
        pkt_dict["format"] = core.PACKET_TYPE_UNCOMPRESSED
        pkt = packets.Packet.factory(pkt_dict)
        self.assertIsInstance(pkt, packets.WeatherPacket)
