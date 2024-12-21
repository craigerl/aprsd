"""Utilities and helper functions."""

import errno
import functools
import math
import os
import re
import sys
import traceback

import update_checker

import aprsd

from .fuzzyclock import fuzzy  # noqa: F401

# Make these available by anyone importing
# aprsd.utils
from .ring_buffer import RingBuffer  # noqa: F401

if sys.version_info.major == 3 and sys.version_info.minor >= 3:
    from collections.abc import MutableMapping
else:
    from collections.abc import MutableMapping


def singleton(cls):
    """Make a class a Singleton class (only one instance)"""

    @functools.wraps(cls)
    def wrapper_singleton(*args, **kwargs):
        if wrapper_singleton.instance is None:
            wrapper_singleton.instance = cls(*args, **kwargs)
        return wrapper_singleton.instance

    wrapper_singleton.instance = None
    return wrapper_singleton


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


def rgb_from_name(name):
    """Create an rgb tuple from a string."""
    hash = 0
    for char in name:
        hash = ord(char) + ((hash << 5) - hash)
    red = hash & 255
    green = (hash >> 8) & 255
    blue = (hash >> 16) & 255
    return red, green, blue


def hextriplet(colortuple):
    """Convert a color tuple to a hex triplet."""
    return "#" + "".join(f"{i:02X}" for i in colortuple)


def hex_from_name(name):
    """Create a hex color from a string."""
    return hextriplet(rgb_from_name(name))


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
        if isinstance(v, MutableMapping):
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

    if m:
        return {key: float(val) for key, val in m.groupdict().items()}
    else:
        return {}


def load_entry_points(group):
    """Load all extensions registered to the given entry point group"""
    try:
        import importlib_metadata
    except ImportError:
        # For python 3.10 and later
        import importlib.metadata as importlib_metadata

    eps = importlib_metadata.entry_points(group=group)
    for ep in eps:
        try:
            ep.load()
        except Exception as e:
            print(
                f"Extension {ep.name} of group {group} failed to load with {e}",
                file=sys.stderr,
            )
            print(traceback.format_exc(), file=sys.stderr)


def calculate_initial_compass_bearing(point_a, point_b):
    """
    Calculates the bearing between two points.
    The formulae used is the following:
        θ = atan2(sin(Δlong).cos(lat2),
                  cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
    :Parameters:
      - `pointA: The tuple representing the latitude/longitude for the
        first point. Latitude and longitude must be in decimal degrees
      - `pointB: The tuple representing the latitude/longitude for the
        second point. Latitude and longitude must be in decimal degrees
    :Returns:
      The bearing in degrees
    :Returns Type:
      float
    """
    if (type(point_a) != tuple) or (type(point_b) != tuple):  # noqa: E721
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(float(point_a[0]))
    lat2 = math.radians(float(point_b[0]))

    diff_long = math.radians(float(point_b[1]) - float(point_a[1]))

    x = math.sin(diff_long) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(diff_long)
    )

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing


def degrees_to_cardinal(bearing, full_string=False):
    if full_string:
        directions = [
            "North",
            "North-Northeast",
            "Northeast",
            "East-Northeast",
            "East",
            "East-Southeast",
            "Southeast",
            "South-Southeast",
            "South",
            "South-Southwest",
            "Southwest",
            "West-Southwest",
            "West",
            "West-Northwest",
            "Northwest",
            "North-Northwest",
            "North",
        ]
    else:
        directions = [
            "N",
            "NNE",
            "NE",
            "ENE",
            "E",
            "ESE",
            "SE",
            "SSE",
            "S",
            "SSW",
            "SW",
            "WSW",
            "W",
            "WNW",
            "NW",
            "NNW",
            "N",
        ]

    cardinal = directions[round(bearing / 22.5)]
    return cardinal
