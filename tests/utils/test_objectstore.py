import os
import pickle
import shutil
import tempfile
import threading
import unittest
from unittest import mock

from oslo_config import cfg

from aprsd.utils import objectstore

CONF = cfg.CONF


class TestObjectStore(objectstore.ObjectStoreMixin):
    """Test class using ObjectStoreMixin."""

    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()
        self.data = {}


class TestObjectStoreMixin(unittest.TestCase):
    """Unit tests for the ObjectStoreMixin class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        CONF.enable_save = True
        CONF.save_location = self.temp_dir

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test initialization."""
        obj = TestObjectStore()
        self.assertIsNotNone(obj.lock)
        self.assertIsInstance(obj.data, dict)

    def test_len(self):
        """Test __len__() method."""
        obj = TestObjectStore()
        self.assertEqual(len(obj), 0)

        obj.data['key1'] = 'value1'
        self.assertEqual(len(obj), 1)

    def test_iter(self):
        """Test __iter__() method."""
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'
        obj.data['key2'] = 'value2'

        keys = list(iter(obj))
        self.assertIn('key1', keys)
        self.assertIn('key2', keys)

    def test_get_all(self):
        """Test get_all() method."""
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'

        all_data = obj.get_all()
        self.assertEqual(all_data, obj.data)
        self.assertIn('key1', all_data)

    def test_get(self):
        """Test get() method."""
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'

        result = obj.get('key1')
        self.assertEqual(result, 'value1')

        result = obj.get('nonexistent')
        self.assertIsNone(result)

    def test_copy(self):
        """Test copy() method."""
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'

        copied = obj.copy()
        self.assertEqual(copied, obj.data)
        self.assertIsNot(copied, obj.data)  # Should be a copy

    def test_save_filename(self):
        """Test _save_filename() method."""
        obj = TestObjectStore()
        filename = obj._save_filename()

        self.assertIn('testobjectstore', filename.lower())
        self.assertTrue(filename.endswith('.p'))

    def test_save(self):
        """Test save() method."""
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'
        obj.data['key2'] = 'value2'

        obj.save()

        filename = obj._save_filename()
        self.assertTrue(os.path.exists(filename))

        # Verify data was saved
        with open(filename, 'rb') as fp:
            loaded_data = pickle.load(fp)
            self.assertEqual(loaded_data, obj.data)

    def test_save_empty(self):
        """Test save() with empty data."""
        obj = TestObjectStore()

        with mock.patch.object(obj, 'flush') as mock_flush:
            obj.save()
            mock_flush.assert_called()

    def test_save_disabled(self):
        """Test save() when saving is disabled."""
        CONF.enable_save = False
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'

        obj.save()

        filename = obj._save_filename()
        self.assertFalse(os.path.exists(filename))

    def test_load(self):
        """Test load() method."""
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'
        obj.save()

        # Create new instance
        obj2 = TestObjectStore()
        obj2.data = {}
        obj2.load()

        self.assertEqual(obj2.data, obj.data)

    def test_load_no_file(self):
        """Test load() when file doesn't exist."""
        obj = TestObjectStore()
        obj.data = {}

        with mock.patch('aprsd.utils.objectstore.LOG') as mock_log:
            obj.load()
            mock_log.debug.assert_called()

    def test_load_corrupted_file(self):
        """Test load() with corrupted pickle file."""
        obj = TestObjectStore()
        filename = obj._save_filename()

        # Create corrupted file
        with open(filename, 'wb') as fp:
            fp.write(b'corrupted data')

        with mock.patch('aprsd.utils.objectstore.LOG') as mock_log:
            obj.load()
            mock_log.error.assert_called()
            self.assertEqual(obj.data, {})

    def test_load_disabled(self):
        """Test load() when saving is disabled."""
        CONF.enable_save = False
        obj = TestObjectStore()
        obj.data = {}

        obj.load()
        # Should not load anything
        self.assertEqual(obj.data, {})

    def test_flush(self):
        """Test flush() method."""
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'
        obj.save()

        filename = obj._save_filename()
        self.assertTrue(os.path.exists(filename))

        obj.flush()

        self.assertFalse(os.path.exists(filename))
        self.assertEqual(len(obj.data), 0)

    def test_flush_no_file(self):
        """Test flush() when file doesn't exist."""
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'

        # Should not raise exception
        obj.flush()
        self.assertEqual(len(obj.data), 0)

    def test_flush_disabled(self):
        """Test flush() when saving is disabled."""
        CONF.enable_save = False
        obj = TestObjectStore()
        obj.data['key1'] = 'value1'

        obj.flush()
        # When saving is disabled, flush() returns early without clearing data
        self.assertEqual(len(obj.data), 1)

    def test_init_store(self):
        """Test _init_store() method."""
        # Should create directory if it doesn't exist
        TestObjectStore()
        self.assertTrue(os.path.exists(self.temp_dir))

    def test_init_store_existing(self):
        """Test _init_store() with existing directory."""
        # Should not raise exception
        TestObjectStore()._init_store()

    def test_thread_safety(self):
        """Test thread safety of operations."""
        import threading

        obj = TestObjectStore()
        results = []
        errors = []

        def add_data(i):
            try:
                obj.data[f'key{i}'] = f'value{i}'
                results.append(len(obj.data))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_data, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have no errors
        self.assertEqual(len(errors), 0)
        # All operations should complete
        self.assertGreater(len(obj.data), 0)
