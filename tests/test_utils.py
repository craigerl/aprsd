from aprsd import utils

import unittest

import pytest

class test_config(unittest.TestCase):

    # test to validate default sections of config yaml are present
    def test_get_config_default(self):
        result = utils.get_config(utils.DEFAULT_CONFIG_FILE)
        assert result.__contains__("aprs")
        assert result.__contains__("aprsd")
        assert result.__contains__("ham")
        assert result.__contains__("imap")
        assert result.__contains__("shortcuts")
        assert result.__contains__("smtp")
        assert len(result) == 6
        assert isinstance(result,dict)

    def test_get_config_aprsd_keys(self):
        result = utils.get_config(utils.DEFAULT_CONFIG_FILE)
        aprsd_keys = result["aprsd"]
        print("\n****************")
        assert aprsd_keys.__contains__("plugin_dir")
        assert aprsd_keys.__contains__("enabled_plugins")
        # if there are any critical values that need to be validated in the default aprsd config, add them here

    def test_get_config_does_not_exist(self):
        bad_file = "\\foo\\bar\\NoFile.yaml"
        result = utils.get_config(bad_file)
        assert result.__contains__(bad_file)
