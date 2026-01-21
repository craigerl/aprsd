import sys
import unittest
from unittest import mock

from click.testing import CliRunner

from aprsd.main import cli


class TestSampleConfigCommand(unittest.TestCase):
    """Unit tests for the sample_config command."""

    def _create_mock_entry_point(self, name):
        """Create a mock entry point object."""
        mock_entry = mock.Mock()
        mock_entry.name = name
        mock_entry.group = 'oslo.config.opts'
        return mock_entry

    @mock.patch('aprsd.main.generator.generate')
    @mock.patch('aprsd.main.imp.entry_points')
    @mock.patch('aprsd.main.metadata_version')
    def test_sample_config_default_ini_output(
        self, mock_version, mock_entry_points, mock_generate
    ):
        """Test sample_config command outputs INI format by default."""
        mock_version.return_value = '1.0.0'
        # Mock entry_points to return at least one aprsd entry point
        # so that get_namespaces() returns a non-empty list
        if sys.version_info >= (3, 10):
            mock_entry_points.return_value = [
                self._create_mock_entry_point('aprsd.conf')
            ]
        else:
            # For Python < 3.10, entry_points() returns a dict-like object
            mock_entry = self._create_mock_entry_point('aprsd.conf')
            mock_dict = {'oslo.config.opts': [mock_entry]}
            mock_entry_points.return_value = mock_dict

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ['sample-config'],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Verify generator.generate was called
        mock_generate.assert_called_once()
        # The conf object passed should not have format_ set to 'json'
        call_args = mock_generate.call_args
        conf_obj = call_args[0][0]
        # When output_json is False, format_ should not be set to 'json'
        assert not hasattr(conf_obj, 'format_') or conf_obj.format_ != 'json'

    @mock.patch('rich.console.Console')
    @mock.patch('aprsd.main.generator.generate')
    @mock.patch('aprsd.main.imp.entry_points')
    @mock.patch('aprsd.main.metadata_version')
    def test_sample_config_json_output(
        self, mock_version, mock_entry_points, mock_generate, mock_console
    ):
        """Test sample_config command with --output-json flag outputs JSON format."""
        mock_version.return_value = '1.0.0'
        # Mock entry_points to return at least one aprsd entry point
        if sys.version_info >= (3, 10):
            mock_entry_points.return_value = [
                self._create_mock_entry_point('aprsd.conf')
            ]
        else:
            # For Python < 3.10, entry_points() returns a dict-like object
            mock_entry = self._create_mock_entry_point('aprsd.conf')
            mock_dict = {'oslo.config.opts': [mock_entry]}
            mock_entry_points.return_value = mock_dict

        # Mock generator.generate to write JSON to stdout
        # This simulates what oslo.config generator does when format_='json'
        def generate_side_effect(conf):
            import sys

            json_output = '{"test": "config", "version": "1.0"}'
            sys.stdout.write(json_output)

        mock_generate.side_effect = generate_side_effect

        # Mock the Console
        mock_console_instance = mock.Mock()
        mock_console.return_value = mock_console_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ['sample-config', '--output-json'],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Verify generator.generate was called
        mock_generate.assert_called_once()
        # Verify Console was instantiated
        mock_console.assert_called_once()
        # Verify print_json was called with parsed JSON
        mock_console_instance.print_json.assert_called_once()
        call_args = mock_console_instance.print_json.call_args
        # The data argument should be a dict (parsed JSON)
        assert isinstance(call_args[1]['data'], dict)
        assert call_args[1]['data'] == {'test': 'config', 'version': '1.0'}
        # Verify that conf.format_ was set to 'json' before generate was called
        generate_call_conf = mock_generate.call_args[0][0]
        assert generate_call_conf.format_ == 'json'

    @mock.patch('aprsd.main.generator.generate')
    @mock.patch('aprsd.main.imp.entry_points')
    @mock.patch('aprsd.main.metadata_version')
    def test_sample_config_without_flag(
        self, mock_version, mock_entry_points, mock_generate
    ):
        """Test sample_config command without --output-json flag (explicit default)."""
        mock_version.return_value = '1.0.0'
        # Mock entry_points to return at least one aprsd entry point
        if sys.version_info >= (3, 10):
            mock_entry_points.return_value = [
                self._create_mock_entry_point('aprsd.conf')
            ]
        else:
            # For Python < 3.10, entry_points() returns a dict-like object
            mock_entry = self._create_mock_entry_point('aprsd.conf')
            mock_dict = {'oslo.config.opts': [mock_entry]}
            mock_entry_points.return_value = mock_dict

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ['sample-config'],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Verify generator.generate was called
        mock_generate.assert_called_once()
        # Verify format_ was not set to 'json'
        call_args = mock_generate.call_args
        conf_obj = call_args[0][0]
        assert not hasattr(conf_obj, 'format_') or conf_obj.format_ != 'json'
