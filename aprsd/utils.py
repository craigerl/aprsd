"""Utilities and helper functions."""

import collections
import errno
import functools
import os
import re
import threading

import update_checker

import aprsd


def synchronized(wrapped):
    lock = threading.Lock()

    @functools.wraps(wrapped)
    def _wrap(*args, **kwargs):
        with lock:
            return wrapped(*args, **kwargs)

    return _wrap


def env(*vars, **kwargs):
    """This returns the first environment variable set.
    if none are non-empty, defaults to '' or keyword arg default
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get("default", "")


def mkdir_p(path):
    """Make directory and have it work in py2 and py3."""
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >= 2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def insert_str(string, str_to_insert, index):
    return string[:index] + str_to_insert + string[index:]


def end_substr(original, substr):
    """Get the index of the end of the <substr>.

    So you can insert a string after <substr>
    """
    idx = original.find(substr)
    if idx != -1:
        idx += len(substr)
    return idx


def human_size(bytes, units=None):
    """Returns a human readable string representation of bytes"""
    if not units:
        units = [" bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])


def strfdelta(tdelta, fmt="{hours:{width}}:{minutes:{width}}:{seconds:{width}}"):
    d = {
        "days": tdelta.days,
        "width": "02",
    }
    if tdelta.days > 0:
        fmt = "{days} days " + fmt

    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def _check_version():
    # check for a newer version
    try:
        check = update_checker.UpdateChecker()
        result = check.check("aprsd", aprsd.__version__)
        if result:
            # Looks like there is an updated version.
            return 1, result
        else:
            return 0, "APRSD is up to date"
    except Exception:
        # probably can't get in touch with pypi for some reason
        # Lets put up an error and move on.  We might not
        # have internet in this aprsd deployment.
        return 1, "Couldn't check for new version of APRSD"


def flatten_dict(d, parent_key="", sep="."):
    """Flatten a dict to key.key.key = value."""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def parse_delta_str(s):
    if "day" in s:
        m = re.match(
            r"(?P<days>[-\d]+) day[s]*, (?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d[\.\d+]*)",
            s,
        )
    else:
        m = re.match(r"(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d[\.\d+]*)", s)
    return {key: float(val) for key, val in m.groupdict().items()}


class RingBuffer:
    """class that implements a not-yet-full buffer"""

    def __init__(self, size_max):
        self.max = size_max
        self.data = []

    class __Full:
        """class that implements a full buffer"""

        def append(self, x):
            """Append an element overwriting the oldest one."""
            self.data[self.cur] = x
            self.cur = (self.cur + 1) % self.max

        def get(self):
            """return list of elements in correct order"""
            return self.data[self.cur :] + self.data[: self.cur]

        def __len__(self):
            return len(self.data)

    def append(self, x):
        """append an element at the end of the buffer"""

        self.data.append(x)
        if len(self.data) == self.max:
            self.cur = 0
            # Permanently change self's class from non-full to full
            self.__class__ = self.__Full

    def get(self):
        """Return a list of elements from the oldest to the newest."""
        return self.data

    def __len__(self):
        return len(self.data)
