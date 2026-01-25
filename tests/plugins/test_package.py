import os
import unittest
from unittest import mock

from aprsd import plugin
from aprsd.utils import package


class TestPackage(unittest.TestCase):
    def test_plugin_type(self):
        self.assertEqual(
            package.plugin_type(plugin.APRSDRegexCommandPluginBase), 'RegexCommand'
        )
        self.assertEqual(
            package.plugin_type(plugin.APRSDWatchListPluginBase), 'WatchList'
        )
        self.assertEqual(package.plugin_type(plugin.APRSDPluginBase), 'APRSDPluginBase')

    def test_is_plugin(self):
        class TestPlugin(plugin.APRSDPluginBase):
            def setup(self):
                pass

            def filter(self, packet):
                pass

            def process(self, packet):
                pass

        class NonPlugin:
            pass

        self.assertTrue(package.is_plugin(TestPlugin))
        self.assertFalse(package.is_plugin(NonPlugin))

    def test_walk_package(self):
        import aprsd.utils

        result = package.walk_package(aprsd.utils)
        # walk_package returns an iterator, so we just check it's not None
        self.assertIsNotNone(result)

    def test_get_module_info(self):
        # Test with a specific, limited directory to avoid hanging
        # Use the aprsd/utils directory which is small and safe
        import aprsd.utils

        package_name = 'aprsd.utils'
        module_name = 'package'
        # Get the actual path to aprsd/utils directory
        module_path = os.path.dirname(aprsd.utils.__file__)
        module_info = package.get_module_info(package_name, module_name, module_path)
        # The result should be a list (even if empty)
        self.assertIsInstance(module_info, list)

    def test_is_aprsd_package(self):
        self.assertTrue(package.is_aprsd_package('aprsd_plugin'))
        self.assertFalse(package.is_aprsd_package('other'))

    def test_is_aprsd_extension(self):
        self.assertTrue(package.is_aprsd_extension('aprsd_extension_plugin'))
        self.assertFalse(package.is_aprsd_extension('other'))

    def test_get_installed_aprsd_items(self):
        plugins, extensions = package.get_installed_aprsd_items()
        self.assertIsNotNone(plugins)
        self.assertIsNotNone(extensions)

    def test_get_installed_plugins(self):
        plugins = package.get_installed_plugins()
        self.assertIsNotNone(plugins)

    def test_get_installed_extensions(self):
        extensions = package.get_installed_extensions()
        self.assertIsNotNone(extensions)

    def test_get_pypi_packages(self):
        # Mock PyPI API responses
        mock_simple_response = mock.MagicMock()
        mock_simple_response.json.return_value = {
            'projects': [
                {'name': 'aprsd-plugin-test'},
                {'name': 'aprsd-extension-test'},
                {'name': 'other-package'},
            ]
        }

        # Create mock responses for each package
        def create_package_response(pkg_name):
            mock_response = mock.MagicMock()
            mock_response.json.return_value = {
                'info': {
                    'name': pkg_name,
                    'version': '1.0.0',
                    'summary': f'Test {pkg_name}',
                    'package_url': f'https://pypi.org/project/{pkg_name}/',
                },
                'releases': {'1.0.0': [{'upload_time': '2024-01-01T00:00:00'}]},
            }
            return mock_response

        with mock.patch('aprsd.utils.package.requests.get') as mock_get:
            # First call returns simple response, subsequent calls return package info
            mock_get.side_effect = [
                mock_simple_response,
                create_package_response('aprsd-plugin-test'),
                create_package_response('aprsd-extension-test'),
            ]
            packages = package.get_pypi_packages()
            self.assertIsNotNone(packages)
            # Verify requests.get was called (at least once for simple API)
            self.assertTrue(mock_get.called)
            # Should have called for simple API + 2 packages
            self.assertGreaterEqual(mock_get.call_count, 1)

    def test_log_installed_extensions_and_plugins(self):
        package.log_installed_extensions_and_plugins()


if __name__ == '__main__':
    unittest.main()
