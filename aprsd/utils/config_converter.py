"""Utilities for converting oslo_cfg CONF objects to/from JSON."""

import json
from typing import Any, Dict

from oslo_config import cfg


def conf_to_dict(conf: cfg.CONF) -> Dict[str, Any]:
    """Convert an oslo_cfg CONF object to a flat dictionary.

    Converts a CONF object with hierarchical groups into a flat dictionary
    where group options are prefixed with 'group_name.option_name'.

    Args:
        conf: The oslo_cfg CONF object to convert

    Returns:
        A dictionary with configuration values, where secret options are masked

    Example:
        >>> from oslo_config import cfg
        >>> CONF = cfg.CONF
        >>> d = conf_to_dict(CONF)
        >>> print(d.get('aprsd.callsign'))
        'W5XYZ'
    """
    entries = {}

    def _sanitize(opt, value):
        """Obfuscate values of options declared secret."""
        if opt.secret:
            return '*' * 4
        return value

    # Process top-level options
    for opt_name in sorted(conf._opts):
        opt = conf._get_opt_info(opt_name)['opt']
        value = getattr(conf, opt_name)
        sanitized = _sanitize(opt, value)
        entries[opt_name] = sanitized

    # Process group options
    for group_name in sorted(conf._groups):
        group_obj = conf._get_group(group_name)
        group_attr = conf.GroupAttr(conf, group_obj)
        for opt_name in sorted(conf._groups[group_name]._opts):
            opt = conf._get_opt_info(opt_name, group_name)['opt']
            value = getattr(group_attr, opt_name)
            sanitized = _sanitize(opt, value)
            gname_opt_name = f'{group_name}.{opt_name}'
            entries[gname_opt_name] = sanitized

    return entries


def conf_to_json(conf: cfg.CONF, indent: int = 2) -> str:
    """Convert an oslo_cfg CONF object to a JSON string.

    Args:
        conf: The oslo_cfg CONF object to convert
        indent: Number of spaces for indentation (None for compact output)

    Returns:
        A JSON string representation of the configuration

    Example:
        >>> from oslo_config import cfg
        >>> CONF = cfg.CONF
        >>> json_str = conf_to_json(CONF)
        >>> print(json_str)
    """
    config_dict = conf_to_dict(conf)
    return json.dumps(config_dict, indent=indent, default=_json_serializer)


def dict_to_conf(
    config_dict: Dict[str, Any],
    conf: cfg.CONF = None,
    mask_secrets: bool = True,
) -> cfg.CONF:
    """Convert a flat dictionary back to an oslo_cfg CONF object.

    Takes a flat dictionary (with keys like 'group_name.option_name' for grouped
    options) and applies those values to a CONF object. Only updates options that
    exist in the CONF object.

    Args:
        config_dict: The configuration dictionary to convert
        conf: The oslo_cfg CONF object to update (uses cfg.CONF if None)
        mask_secrets: If True, skips options with masked values ('****')

    Returns:
        The updated CONF object

    Example:
        >>> from oslo_config import cfg
        >>> config_dict = {'aprsd.callsign': 'W5XYZ', 'log_level': 'DEBUG'}
        >>> CONF = dict_to_conf(config_dict)
        >>> print(CONF.aprsd.callsign)
        'W5XYZ'

    Note:
        - Options with secret masks ('****') are skipped to avoid overwriting
          with placeholder values
        - Only recognized options in the CONF schema are updated
        - Invalid group/option names are silently skipped
    """
    if conf is None:
        conf = cfg.CONF

    for key, value in config_dict.items():
        # Skip masked secret values
        if mask_secrets and isinstance(value, str) and value == '*' * 4:
            continue

        if '.' in key:
            # Handle grouped options
            group_name, opt_name = key.split('.', 1)
            try:
                # Check if group exists
                if group_name in conf:
                    group = getattr(conf, group_name)
                    # Check if option exists in group
                    if hasattr(group, opt_name):
                        _set_conf_value(conf, group_name, opt_name, value)
            except (KeyError, AttributeError):
                # Skip unrecognized groups
                continue
        else:
            # Handle top-level options
            try:
                if hasattr(conf, key):
                    _set_conf_value(conf, None, key, value)
            except (KeyError, AttributeError):
                # Skip unrecognized options
                continue

    return conf


def json_to_conf(
    json_str: str,
    conf: cfg.CONF = None,
    mask_secrets: bool = True,
) -> cfg.CONF:
    """Convert a JSON string back to an oslo_cfg CONF object.

    Args:
        json_str: The JSON string to parse
        conf: The oslo_cfg CONF object to update (uses cfg.CONF if None)
        mask_secrets: If True, skips options with masked values ('****')

    Returns:
        The updated CONF object

    Raises:
        json.JSONDecodeError: If the JSON string is invalid

    Example:
        >>> json_str = '{"aprsd.callsign": "W5XYZ", "log_level": "DEBUG"}'
        >>> CONF = json_to_conf(json_str)
    """
    config_dict = json.loads(json_str)
    return dict_to_conf(config_dict, conf, mask_secrets)


def _set_conf_value(
    conf: cfg.CONF,
    group_name: str,
    opt_name: str,
    value: Any,
) -> None:
    """Set a configuration value in CONF object with proper type conversion.

    Args:
        conf: The CONF object
        group_name: The group name (None for top-level options)
        opt_name: The option name
        value: The value to set

    Raises:
        KeyError: If the option is not found
    """
    # Get the option metadata
    if group_name:
        opt_info = conf._get_opt_info(opt_name, group_name)
    else:
        opt_info = conf._get_opt_info(opt_name)

    opt = opt_info['opt']

    # Convert value to appropriate type
    converted_value = _convert_value(opt, value)

    # Set the value
    if group_name:
        # For grouped options, we need to set via the group
        group = getattr(conf, group_name)
        setattr(group, opt_name, converted_value)
    else:
        # For top-level options
        setattr(conf, opt_name, converted_value)


def _convert_value(opt, value: Any) -> Any:
    """Convert a value to the appropriate type for an option.

    Handles conversion for oslo_config option types:
    - StrOpt: keeps as string
    - IntOpt: converts to int
    - FloatOpt: converts to float
    - BoolOpt: converts to bool
    - ListOpt: ensures it's a list
    - DictOpt: ensures it's a dict

    Args:
        opt: The oslo_config option object
        value: The value to convert

    Returns:
        The converted value
    """
    if value is None:
        return None

    # Handle string representations
    if isinstance(value, str):
        if isinstance(opt, cfg.IntOpt):
            return int(value)
        elif isinstance(opt, cfg.FloatOpt):
            return float(value)
        elif isinstance(opt, cfg.BoolOpt):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(opt, (cfg.ListOpt, cfg.MultiOpt)):
            # If it's a string representation of a list, parse it
            if value.startswith('[') and value.endswith(']'):
                return json.loads(value)
            return [value] if value else []
        elif isinstance(opt, cfg.DictOpt):
            # If it's a string representation of a dict, parse it
            if value.startswith('{') and value.endswith('}'):
                return json.loads(value)
            return {}
    elif isinstance(value, bool) and not isinstance(opt, cfg.BoolOpt):
        # If we got a bool but it's not a BoolOpt, convert to appropriate type
        if isinstance(opt, cfg.StrOpt):
            return str(value)
        elif isinstance(opt, cfg.IntOpt):
            return int(value)
    elif isinstance(value, (list, tuple)):
        if isinstance(opt, (cfg.ListOpt, cfg.MultiOpt)):
            return list(value)
        elif isinstance(opt, cfg.StrOpt):
            # Convert list to comma-separated string
            return ','.join(str(v) for v in value)
    elif isinstance(value, dict):
        if isinstance(opt, cfg.DictOpt):
            return value
        elif isinstance(opt, cfg.StrOpt):
            return json.dumps(value)

    return value


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for oslo_config types.

    Args:
        obj: The object to serialize

    Returns:
        A JSON-serializable representation of the object
    """
    if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        return list(obj)
    return str(obj)
