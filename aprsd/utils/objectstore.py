import abc
import logging
import os
import pathlib
import pickle

from aprsd import config as aprsd_config


LOG = logging.getLogger("APRSD")


class ObjectStoreMixin(metaclass=abc.ABCMeta):
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
    @abc.abstractmethod
    def is_initialized(self):
        """Return True if the class has been setup correctly.

        If this returns False, the ObjectStore doesn't save anything.

        """

    def __len__(self):
        return len(self.data)

    def get_all(self):
        with self.lock:
            return self.data

    def get(self, id):
        with self.lock:
            return self.data[id]

    def _init_store(self):
        if self.is_initialized():
            sl = self._save_location()
            if not os.path.exists(sl):
                LOG.warning(f"Save location {sl} doesn't exist")
                try:
                    os.makedirs(sl)
                except Exception as ex:
                    LOG.exception(ex)
        else:
            LOG.warning(f"{self.__class__.__name__} is not initialized")

    def _save_location(self):
        save_location = self.config.get("aprsd.save_location", None)
        if not save_location:
            save_location = aprsd_config.DEFAULT_CONFIG_DIR
        return save_location

    def _save_filename(self):
        save_location = self._save_location()

        return "{}/{}.p".format(
            save_location,
            self.__class__.__name__.lower(),
        )

    def _dump(self):
        dump = {}
        with self.lock:
            for key in self.data.keys():
                dump[key] = self.data[key]

        return dump

    def save(self):
        """Save any queued to disk?"""
        if self.is_initialized():
            if len(self) > 0:
                LOG.info(
                    f"{self.__class__.__name__}::Saving"
                    f" {len(self)} entries to disk at"
                    f"{self._save_location()}",
                )
                with open(self._save_filename(), "wb+") as fp:
                    pickle.dump(self._dump(), fp)
            else:
                LOG.debug(
                    "{} Nothing to save, flushing old save file '{}'".format(
                        self.__class__.__name__,
                        self._save_filename(),
                    ),
                )
                self.flush()

    def load(self):
        if self.is_initialized():
            if os.path.exists(self._save_filename()):
                try:
                    with open(self._save_filename(), "rb") as fp:
                        raw = pickle.load(fp)
                        if raw:
                            self.data = raw
                            LOG.debug(
                                f"{self.__class__.__name__}::Loaded {len(self)} entries from disk.",
                            )
                            LOG.debug(f"{self.data}")
                except (pickle.UnpicklingError, Exception) as ex:
                    LOG.error(f"Failed to UnPickle {self._save_filename()}")
                    LOG.error(ex)
                    self.data = {}

    def flush(self):
        """Nuke the old pickle file that stored the old results from last aprsd run."""
        if self.is_initialized():
            if os.path.exists(self._save_filename()):
                pathlib.Path(self._save_filename()).unlink()
            with self.lock:
                self.data = {}
