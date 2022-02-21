class MissingConfigOptionException(Exception):
    """Missing a config option."""
    def __init__(self, config_option):
        self.message = f"Option '{config_option}' was not in config file"


class ConfigOptionBogusDefaultException(Exception):
    """Missing a config option."""
    def __init__(self, config_option, default_fail):
        self.message = (
            f"Config file option '{config_option}' needs to be "
            f"changed from provided default of '{default_fail}'"
        )
