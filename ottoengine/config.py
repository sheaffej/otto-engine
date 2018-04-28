import configparser
import logging
import os

_CONFIG_FILE = "config.ini"


def _parse_boolean(val: str):
    if val:
        if val.upper() in ["TRUE", "YES"]:
            return True
    return False


def print_config():
    for section in _config.sections():
        print("[{}]".format(section))
        for key, val in _config.items(section):
            print("{} = {}".format(key, val))


def _get_config_value(config: configparser, section: str, key: str, required: bool = False):
    if not config[section][key.lower()]:
        logging.error(
            "Missing config in {}: section ({}), key ({})".format(_CONFIG_FILE, section, key)
        )
        if required:
            raise KeyError("Key [{}] {} not found".format(section, key))
    else:
        return config[section][key.lower()]


_config = configparser.ConfigParser()
_files = [_CONFIG_FILE]
if "OTTO_ENGINE_HOME" in os.environ:
    _files.append(os.path.join(os.environ["OTTO_ENGINE_HOME"], _CONFIG_FILE))
_config.read(_files)


# Requried Parameters
_section = "ENGINE"
OTTO_REST_PORT = _get_config_value(_config, _section, "OTTO_REST_PORT", required=True)
HASS_HOST = _get_config_value(_config, _section, "HASS_HOST", required=True)
HASS_PORT = _get_config_value(_config, _section, "HASS_PORT", required=True)
HASS_PASSWORD = _get_config_value(_config, _section, "HASS_PASSWORD", required=True)
HASS_SSL = _parse_boolean(_get_config_value(_config, _section, "HASS_SSL", required=True))
TZ = _get_config_value(_config, _section, "TZ", required=True)
JSON_RULES_DIR = _get_config_value(_config, _section, "JSON_RULES_DIR", required=True)


# Optional Parameters
LOG_LEVEL = logging.INFO
_loglevel = _get_config_value(_config, _section, "LOG_LEVEL")
if _loglevel:
    if "CRITICAL" in _loglevel.upper():
        LOG_LEVEL = logging.CRITICAL
    elif "ERROR" in _loglevel.upper():
        LOG_LEVEL = logging.ERROR
    elif "WARN" in _loglevel.upper():
        LOG_LEVEL = logging.WARN
    elif "DEBUG" in _loglevel.upper():
        LOG_LEVEL = logging.DEBUG
