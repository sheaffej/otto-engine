import configparser
import logging
import os
import shutil

CONFIG_FILE = "config.ini"
CONFIG_EXAMPLE = "/app/config.ini.example"


def _parse_boolean(val: str):
    if val:
        if val.upper() in ["TRUE", "YES"]:
            return True
    return False


def _parse_int(val: str):
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return None


class EngineConfig:

    def __init__(self, config_dir="/config"):
        self._config_file = os.path.join(config_dir, CONFIG_FILE)
        self._config = configparser.ConfigParser()

        self.rest_port = 5000
        self.test_websocket_port = None  # Normally the HA port 8123
        self.hass_host = "localhost"
        self.hass_port = 8123
        self.hass_token = None
        self.hass_ssl = False
        self.tz = "America/Los_Angeles"
        self.json_rules_dir = "./json_rules"
        self.log_level = logging.INFO

    def load(self):
        self._load_config_file()
        self._read_parameters()
        return self

    def _get(self, section: str, key: str, required: bool = False):
        if key.lower() not in self._config[section]:
            if required:
                print(
                    "Missing required config in {}: section ({}), key ({})".format(
                        self._config_file, section, key))
                raise KeyError("Key [{}] {} not found".format(section, key))
            else:
                return None
        else:
            return self._config[section][key.lower()]

    def _load_config_file(self):
        # Load configuration file
        if not os.path.isfile(self._config_file):
            shutil.copy(CONFIG_EXAMPLE, self._config_file)

        files = [self._config_file]
        if "OTTO_ENGINE_HOME" in os.environ:
            files.append(os.path.join(os.environ["OTTO_ENGINE_HOME"], self._config_file))
        self._config.read(files)

    def _read_parameters(self):
        # Requried Parameters
        self.rest_port = _parse_int(self._get("ENGINE", "OTTO_REST_PORT", required=True))
        self.hass_host = self._get("ENGINE", "HASS_HOST", required=True)
        self.hass_port = _parse_int(self._get("ENGINE", "HASS_PORT", required=True))
        self.hass_token = self._get("ENGINE", "HASS_TOKEN", required=True)
        self.hass_ssl = _parse_boolean(self._get("ENGINE", "HASS_SSL", required=True))
        self.tz = self._get("ENGINE", "TZ", required=True)
        self.json_rules_dir = self._get("ENGINE", "JSON_RULES_DIR", required=True)

        # Optional Parameters
        self.log_level = self._get("ENGINE", "LOG_LEVEL")
        if self.log_level:
            if "CRITICAL" in self.log_level.upper():
                self.log_level = logging.CRITICAL
            elif "ERROR" in self.log_level.upper():
                self.log_level = logging.ERROR
            elif "WARN" in self.log_level.upper():
                self.log_level = logging.WARN
            elif "DEBUG" in self.log_level.upper():
                self.log_level = logging.DEBUG
        else:
            self.log_level = logging.INFO

        self.test_websocket_port = _parse_int(self._get("ENGINE", "TEST_WEBSOCKET_PORT"))
