import logging
import os
import pathlib
import pickle
import threading

from oslo_config import cfg

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

    def __init__(self):
        self.lock = threading.RLock()

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

        return '{}/{}.p'.format(
            save_location,
            self.__class__.__name__.lower(),
        )

    def save(self):
        """Save any queued to disk?"""
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
                with open(save_filename, 'wb+') as fp:
                    pickle.dump(self.data, fp)
        else:
            LOG.debug(
                "{} Nothing to save, flushing old save file '{}'".format(
                    self.__class__.__name__,
                    save_filename,
                ),
            )
            self.flush()

    def load(self):
        if not CONF.enable_save:
            return
        if os.path.exists(self._save_filename()):
            try:
                with open(self._save_filename(), 'rb') as fp:
                    raw = pickle.load(fp)
                    if raw:
                        self.data = raw
                        LOG.debug(
                            f'{self.__class__.__name__}::Loaded {len(self)} entries from disk.',
                        )
                    else:
                        LOG.debug(f'{self.__class__.__name__}::No data to load.')
            except (pickle.UnpicklingError, Exception) as ex:
                LOG.error(f'Failed to UnPickle {self._save_filename()}')
                LOG.error(ex)
                self.data = {}
        else:
            LOG.debug(f'{self.__class__.__name__}::No save file found.')

    def flush(self):
        """Nuke the old pickle file that stored the old results from last aprsd run."""
        if not CONF.enable_save:
            return
        if os.path.exists(self._save_filename()):
            pathlib.Path(self._save_filename()).unlink()
        with self.lock:
            self.data = {}
