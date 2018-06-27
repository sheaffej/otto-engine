#!/usr/bin/env python

import unittest

from ottoengine import config


class TestConfig(unittest.TestCase):

    def test_read_parameters(self):
        params = [
            # INI section, INI parameter, INI value, Obj attribute, Value

            ("OTTO_REST_PORT", "5000", "rest_port", 5000),
            ("HASS_HOST", "localhost", "hass_host", "localhost"),
            ("HASS_PORT", "8123", "hass_port", 8123),
            ("HASS_PASSWORD", "password", "hass_password", "password"),
            ("HASS_SSL", "no", "hass_ssl", False),
            ("TZ", "America/Los_Angeles", "tz", "America/Los_Angeles"),
            ("JSON_RULES_DIR", "json_rules", "json_rules_dir", "json_rules"),
            ("LOG_LEVEL", "INFO", "log_level", "INFO"),
        ]
        section = "ENGINE"
        cfg = config.EngineConfig()
        cfg._config.add_section(section)
        for param, ini_val, obj_name, obj_val in params:
            print("Setting {} to {}".format(param, ini_val))
            cfg._config.set(section, param, ini_val)

        cfg._read_parameters()
        for param, ini_val, obj_name, obj_val in params:
            print("Expecting {} to be {}".format(obj_name, obj_val))
            self.assertEqual(getattr(cfg, obj_name), obj_val)


if __name__ == "__main__":
    unittest.main()
