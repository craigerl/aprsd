import unittest
from unittest import mock

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

    @mock.patch("aprsd.packets.core.GPSPacket._build_time_zulu")
    def test_packet_format_rain_1h(self, mock_time_zulu):

        mock_time_zulu.return_value = "221450"

        wx = packets.WeatherPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            timestamp=1671721164.1112509,
        )
        wx.prepare()

        expected = "KFAKE>KMINE,WIDE1-1,WIDE2-1:@221450z0.0/0.0_000/000g000t000r000p000P000h00b00000"
        self.assertEqual(expected, wx.raw)
        rain_location = 59
        self.assertEqual(rain_location, wx.raw.find("r000"))

        wx.rain_1h = 1.11
        wx.prepare()
        expected = "KFAKE>KMINE,WIDE1-1,WIDE2-1:@221450z0.0/0.0_000/000g000t000r111p000P000h00b00000"
        self.assertEqual(expected, wx.raw)

        wx.rain_1h = 0.01
        wx.prepare()
        expected = "KFAKE>KMINE,WIDE1-1,WIDE2-1:@221450z0.0/0.0_000/000g000t000r001p000P000h00b00000"
        self.assertEqual(expected, wx.raw)
