import unittest

from aprsd import exception


class TestExceptions(unittest.TestCase):
    """Unit tests for custom exception classes."""

    def test_missing_config_option_exception(self):
        """Test MissingConfigOptionException."""
        exc = exception.MissingConfigOptionException('test.option')
        self.assertIsInstance(exc, Exception)
        self.assertIn('test.option', exc.message)
        self.assertIn("Option 'test.option' was not in config file", exc.message)

    def test_config_option_bogus_default_exception(self):
        """Test ConfigOptionBogusDefaultException."""
        exc = exception.ConfigOptionBogusDefaultException(
            'test.option', 'default_value'
        )
        self.assertIsInstance(exc, Exception)
        self.assertIn('test.option', exc.message)
        self.assertIn('default_value', exc.message)
        self.assertIn('needs to be changed', exc.message)

    def test_aprs_client_not_configured_exception(self):
        """Test APRSClientNotConfiguredException."""
        exc = exception.APRSClientNotConfiguredException()
        self.assertIsInstance(exc, Exception)
        self.assertEqual(exc.message, 'APRS client is not configured.')

    def test_exception_inheritance(self):
        """Test that exceptions inherit from Exception."""
        exc1 = exception.MissingConfigOptionException('test')
        exc2 = exception.ConfigOptionBogusDefaultException('test', 'default')
        exc3 = exception.APRSClientNotConfiguredException()

        self.assertIsInstance(exc1, Exception)
        self.assertIsInstance(exc2, Exception)
        self.assertIsInstance(exc3, Exception)

    def test_exception_raising(self):
        """Test that exceptions can be raised and caught."""
        with self.assertRaises(exception.MissingConfigOptionException) as context:
            raise exception.MissingConfigOptionException('test.option')

        self.assertIn('test.option', str(context.exception))
