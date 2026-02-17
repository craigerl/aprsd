import json
import logging
import os
import pathlib

from oslo_config import cfg

from aprsd.utils.json import PacketJSONDecoder, SimpleJSONEncoder

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class ObjectStoreMixin:
    """Class 'MIXIN' intended to save/load object data.

    The asumption of how this mixin is used:
      The using class has to have a:
         * data in self.data as a dictionary
         * a self.lock thread lock
         * Class must specify self.save_file as the location.


    When APRSD quits, it calls save()
    When APRSD Starts, it calls load()
    aprsd server -f (flush) will wipe all saved objects.
    """

    # Child class must create the lock.
    lock = None

    def __len__(self):
        with self.lock:
            return len(self.data)

    def __iter__(self):
        with self.lock:
            return iter(self.data)

    def get_all(self):
        with self.lock:
            return self.data

    def get(self, key):
        with self.lock:
            return self.data.get(key)

    def copy(self):
        with self.lock:
            return self.data.copy()

    def _init_store(self):
        if not CONF.enable_save:
            return
        sl = CONF.save_location
        if not os.path.exists(sl):
            LOG.warning(f"Save location {sl} doesn't exist")
            try:
                os.makedirs(sl)
            except Exception as ex:
                LOG.exception(ex)

    def _save_filename(self):
        save_location = CONF.save_location

        return '{}/{}.json'.format(
            save_location,
            self.__class__.__name__.lower(),
        )

    def _old_save_filename(self):
        """Return the old pickle filename for migration detection."""
        save_location = CONF.save_location
        return '{}/{}.p'.format(
            save_location,
            self.__class__.__name__.lower(),
        )

    def save(self):
        """Save any queued to disk as JSON."""
        if not CONF.enable_save:
            return
        self._init_store()
        save_filename = self._save_filename()
        if len(self) > 0:
            LOG.debug(
                f'{self.__class__.__name__}::Saving'
                f' {len(self)} entries to disk at '
                f'{save_filename}',
            )
            with self.lock:
                with open(save_filename, 'w') as fp:
                    json.dump(self.data, fp, cls=SimpleJSONEncoder, indent=2)
        else:
            LOG.debug(
                "{} Nothing to save, flushing old save file '{}'".format(
                    self.__class__.__name__,
                    save_filename,
                ),
            )
            self.flush()

    def load(self):
        """Load data from JSON file."""
        if not CONF.enable_save:
            return

        json_file = self._save_filename()
        pickle_file = self._old_save_filename()

        with self.lock:
            # Check if old pickle file exists but JSON doesn't
            if not os.path.exists(json_file) and os.path.exists(pickle_file):
                LOG.warning(
                    f'{self.__class__.__name__}::Found old pickle file {pickle_file}. '
                    f'Please run "aprsd dev migrate-pickle" to convert to JSON format. '
                    f'Skipping load to avoid security risk.'
                )
                return

            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r') as fp:
                        raw = json.load(fp, cls=PacketJSONDecoder)
                        if raw:
                            self.data = raw
                            # Special handling for OrderedDict in PacketList
                            if hasattr(self, '_restore_ordereddict'):
                                self._restore_ordereddict()
                            LOG.debug(
                                f'{self.__class__.__name__}::Loaded {len(self)} entries from disk.',
                            )
                        else:
                            LOG.debug(f'{self.__class__.__name__}::No data to load.')
                except (json.JSONDecodeError, Exception) as ex:
                    LOG.error(f'Failed to load JSON from {json_file}')
                    LOG.exception(ex)
                    self.data = {}
            else:
                LOG.debug(f'{self.__class__.__name__}::No save file found.')

    def flush(self):
        """Remove the JSON save file and clear data."""
        if not CONF.enable_save:
            return
        with self.lock:
            if os.path.exists(self._save_filename()):
                pathlib.Path(self._save_filename()).unlink()
            self.data = {}
