import unittest
from unittest import mock

import aprslib

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
        pkt = packets.factory(pkt_dict)

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
        pkt = packets.factory(pkt_dict)
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

    def test_beacon_factory(self):
        """Test to ensure a beacon packet is created."""
        packet_raw = "WB4BOR-12>APZ100,WIDE2-1:@161647z3724.15N107847.58W$ APRSD WebChat"
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.BeaconPacket)

    def test_reject_factory(self):
        """Test to ensure a reject packet is created."""
        packet_raw = "HB9FDL-1>APK102,HB9FM-4*,WIDE2,qAR,HB9FEF-11::REPEAT   :rej4139"
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.RejectPacket)

    def test_thirdparty_factory(self):
        """Test to ensure a third party packet is created."""
        packet_raw = "GTOWN>APDW16,WIDE1-1,WIDE2-1:}KM6LYW-9>APZ100,TCPIP,GTOWN*::KM6LYW   :KM6LYW: 19 Miles SW"
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.ThirdPartyPacket)

    def test_weather_factory(self):
        """Test to ensure a weather packet is created."""
        packet_raw = "FW9222>APRS,TCPXX*,qAX,CWOP-6:@122025z2953.94N/08423.77W_232/003g006t084r000p032P000h80b10157L745.DsWLL"
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.WeatherPacket)

    def test_mice_factory(self):
        packet_raw = 'kh2sr-15>S7TSYR,WIDE1-1,WIDE2-1,qAO,KO6KL-1:`1`7\x1c\x1c.#/`"4,}QuirkyQRP 4.6V  35.3C S06'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.MicEPacket)
