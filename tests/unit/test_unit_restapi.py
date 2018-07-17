#!/usr/bin/env python

import logging
import json
import unittest

from ottoengine import restapi, utils, state, helpers
from ottoengine.model.rule_objects import AutomationRule


class MockOttoEngine:
    def __init__(self):
        # This is intentionally named different from OttoEngine's public state attribute
        # to ensure the REST API is not accessing the OttoEngine state directly.
        # The restapi runs in its own thread, and therefore should only be going through
        # threadsafe methods.
        self._hidden_states = state.OttoEngineState()

        self._hidden_states.set_engine_state("start_time", helpers.nowutc())
        
        # Add some rules
        for i in range(1, 6):
            id = str(i)*5
            self._hidden_states.add_rule(
                AutomationRule(id, "Rule {}".format(id), enabled=True, group="unittest")
            )

    def get_state_threadsafe(self, group, key):
        return self._hidden_states.get_state(group, key)

    # def get_all_entity_state_threadsafe(self) -> list:
    #     return self._hidden_states.get_all_entity_state_copy()

    def reload_rules_threadsafe(self) -> bool:
        return {"success": True}

    def get_rules_threadsafe(self) -> list:
        return self._hidden_states.get_rules()


    # def get_state_threadsafe(self, group, key):
    # def get_entity_state_threadsafe(self, entity_id):
    # def get_rules_threadsafe(self) -> list:
    # def get_rule_threadsafe(self, rule_id) -> dict:
    # def delete_rule_threadsafe(self, rule_id) -> bool:
    # def get_entities_threadsafe(self) -> list:
    # def get_services_threadsafe(self) -> list:
    # def get_logs_threadsafe(self) -> list:
    # def save_rule_threadsafe(self, rule_dict):
    # def check_timespec_threadsafe(self, spec_dict):


class TestRestAPI(unittest.TestCase):
    def setUp(self):
        self.eng = MockOttoEngine()
        self.app = restapi.app.test_client()
        restapi.engine_obj = self.eng
        utils.setup_logging(logging.DEBUG)
        print()

    # Tests: @app.route('/rest/ping')
    def test_route_ping(self):
        resp = self.app.get("/rest/ping").get_json()
        print(resp)
        self.assertEqual(resp["success"], True)

    # Tests: @app.route('/rest/reload', methods=['GET'])
    def test_route_reload(self):
        resp = self.app.get("/rest/reload").get_json()
        print(resp)
        self.assertEqual(resp["success"], True)
        self.assertIn("Rules reloaded successfully", resp["message"])

    # Tests: @app.route('/rest/rules', methods=['GET'])
    def test_route_rules(self):
        resp = self.app.get("/rest/rules").get_json()
        print(resp)
        resp_data = resp.get("data")
        self.assertEqual(len(resp_data), len(self.eng._hidden_states._rules))
        for rule in resp_data:
            self.assertIsNotNone(rule["id"])
            self.assertIn("Rule ", rule["description"])
            self.assertTrue(rule["enabled"])
            self.assertEqual(rule["group"], "unittest")


    # Tests: @app.route('/rest/entities', methods=['GET'])
    # Tests: @app.route('/rest/services', methods=['GET'])
    # Tests: @app.route('/rest/rule', methods=['PUT'])
    # Tests: @app.route('/rest/rule/<rule_id>', methods=['GET', 'PUT', 'DELETE'])
    # Tests: @app.route('/rest/clock/check', methods=['PUT'])
    # Tests: @app.route('/rest/logs', methods=['GET'])

    # Not covered:
    # @app.route('/shutdown', methods=['GET'])
