from unittest import mock

from aprsd.plugins import fortune as fortune_plugin

from .. import fake, test_plugin


class TestFortunePlugin(test_plugin.TestPlugin):
    @mock.patch("shutil.which")
    def test_fortune_fail(self, mock_which):
        mock_which.return_value = None
        fortune = fortune_plugin.FortunePlugin(self.config)
        expected = "FortunePlugin isn't enabled"
        packet = fake.fake_packet(message="fortune")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("subprocess.check_output")
    @mock.patch("shutil.which")
    def test_fortune_success(self, mock_which, mock_output):
        mock_which.return_value = "/usr/bin/games/fortune"
        mock_output.return_value = "Funny fortune"
        fortune = fortune_plugin.FortunePlugin(self.config)

        expected = "Funny fortune"
        packet = fake.fake_packet(message="fortune")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)
