import datetime
import decimal
import json
import sys

from aprsd.packets import core


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            args = (
                'year',
                'month',
                'day',
                'hour',
                'minute',
                'second',
                'microsecond',
            )
            return {
                '__type__': 'datetime.datetime',
                'args': [getattr(obj, a) for a in args],
            }
        elif isinstance(obj, datetime.date):
            args = ('year', 'month', 'day')
            return {
                '__type__': 'datetime.date',
                'args': [getattr(obj, a) for a in args],
            }
        elif isinstance(obj, datetime.time):
            args = ('hour', 'minute', 'second', 'microsecond')
            return {
                '__type__': 'datetime.time',
                'args': [getattr(obj, a) for a in args],
            }
        elif isinstance(obj, datetime.timedelta):
            args = ('days', 'seconds', 'microseconds')
            return {
                '__type__': 'datetime.timedelta',
                'args': [getattr(obj, a) for a in args],
            }
        elif isinstance(obj, decimal.Decimal):
            return {
                '__type__': 'decimal.Decimal',
                'args': [str(obj)],
            }
        else:
            return super().default(obj)


class SimpleJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return str(obj)
        elif isinstance(obj, datetime.time):
            return str(obj)
        elif isinstance(obj, datetime.timedelta):
            return str(obj)
        elif isinstance(obj, decimal.Decimal):
            return str(obj)
        elif isinstance(obj, core.Packet):
            return obj.to_dict()
        else:
            return super().default(obj)


class EnhancedJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            object_hook=self.object_hook,
            **kwargs,
        )

    def object_hook(self, d):
        if '__type__' not in d:
            return d
        o = sys.modules[__name__]
        for e in d['__type__'].split('.'):
            o = getattr(o, e)
        args, kwargs = d.get('args', ()), d.get('kwargs', {})
        return o(*args, **kwargs)


class PacketJSONDecoder(json.JSONDecoder):
    """Custom JSON decoder for reconstructing Packet objects from dicts.

    This decoder is used by ObjectStoreMixin to reconstruct Packet objects
    when loading from JSON files. It handles:
    - Packet objects and their subclasses (AckPacket, MessagePacket, etc.)
    - Datetime objects stored as ISO format strings
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            object_hook=self.object_hook,
            **kwargs,
        )

    def object_hook(self, obj):
        """Reconstruct objects from their dict representation."""
        if not isinstance(obj, dict):
            return obj

        # Check if this looks like a Packet object
        # Packets have _type, from_call, and to_call fields
        if '_type' in obj and 'from_call' in obj and 'to_call' in obj:
            try:
                # Use the factory function to reconstruct the correct packet type
                return core.factory(obj)
            except Exception:
                # If reconstruction fails, return as dict
                # This prevents data loss if packet format changes
                return obj

        # Handle datetime strings (ISO format)
        # Check for common datetime field names
        for key in ['last', 'timestamp', 'last_send_time']:
            if key in obj and isinstance(obj[key], str):
                try:
                    # Try to parse as datetime
                    obj[key] = datetime.datetime.fromisoformat(obj[key])
                except (ValueError, TypeError, AttributeError):
                    # Not a datetime, leave as string
                    pass

        return obj
