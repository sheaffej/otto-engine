#!/usr/bin/env python3

import copy
import json
import os
import requests
import unittest

from ottoengine.testing import restapi_helpers

RESTURL = "http://localhost:5000"


class TestRulePersistence(unittest.TestCase):

    def setUp(self):
        print()
        self.rule12345 = {
            "data": {
                "id": "12345",
                "description": "Turn everything on after a 3 second delay if both triggered",
                "enabled": True,
                "group": "Testing",
                "triggers": [
                    {
                        "platform": "state",
                        "entity_id": "input_boolean.state_home_occupied",
                        "to": "on",
                        "from": "off"
                    },
                    {
                        "platform": "state",
                        "entity_id": "input_boolean.state_motion_in_home",
                        "to": "on",
                        "from": "off"
                    },
                    {
                        "platform": "numeric_state",
                        "entity_id": "input_slider.temp_slider",
                        "above_value": 80
                    },
                    {
                        "platform": "event",
                        "event_type": "call_service",
                        "event_data": {
                            "service": "test_service"
                        }
                    }
                ],
                "rule_condition": {
                    "condition": "and",
                    "conditions": [
                        {
                            "condition": "state",
                            "entity_id": "input_boolean.state_home_occupied",
                            "state": "on"
                        },
                        {
                            "condition": "state",
                            "entity_id": "input_boolean.state_motion_in_home",
                            "state": "on"
                        }
                    ]
                },
                "actions": [
                    {
                        "action_condition": {
                            "condition": "state",
                            "entity_id": "input_boolean.state_home_occupied",
                            "state": "on"
                        },
                        "action_sequence": [
                            {
                                "domain": "input_boolean",
                                "service": "turn_on",
                                "data": {
                                    "entity_id": "input_boolean.action_light"
                                }
                            },
                            {
                                "domain": "input_boolean",
                                "service": "turn_on",
                                "data": {
                                    "entity_id": "input_boolean.action_siren"
                                }
                            }
                        ]
                    },
                    {
                        "action_condition": {
                            "condition": "state",
                            "entity_id": "input_boolean.state_motion_in_home",
                            "state": "on"
                        },
                        "action_sequence": [
                            {
                                "delay": "00:00:03"
                            },
                            {
                                "domain": "input_boolean",
                                "service": "turn_on",
                                "data": {
                                    "entity_id": "input_boolean.action_light2"
                                }
                            },
                            {
                                "domain": "input_boolean",
                                "service": "turn_on",
                                "data": {
                                    "entity_id": "input_boolean.action_siren2"
                                }
                            }
                        ]
                    }
                ]
            }
        }

    def test_1_put_bad_rule(self):
        # PUT bad rule
        data = {"data": {"name": "John", "age": 44}}
        resp = requests.put(RESTURL + "/rest/rule", json=data).json()
        print(resp)
        self.assertEqual(resp.get("success"), False)
        self.assertEqual(resp.get("id"), None)

    def test_2_get_missing_rule(self):
        # GET missing rule 1234
        resp = requests.get(RESTURL + "/rest/rule/1234").json()
        print(resp)
        self.assertEqual(resp.get("success"), False)
        self.assertEqual(resp.get("id"), "1234")

    def test_3_put_good_rule(self):
        # PUT good rule /rest/rule with ID 1234
        resp = requests.put(RESTURL + "/rest/rule", json=self.rule12345).json()
        print(resp)
        self.assertEqual(resp.get("success"), True)
        self.assertEqual(resp.get("id"), "12345")

    def test_4_put_rule_wrong_id(self):
        # Re-PUT good rule with wrong ID /rest/rule/4545
        # This should succeed, and return the right rule ID (12345)
        # This also tests updating a rule by overwritting it
        resp = requests.put(RESTURL + "/rest/rule/4545", json=self.rule12345).json()
        print(resp)
        self.assertEqual(resp.get("success"), True)
        self.assertEqual(resp.get("id"), "12345")

    def test_5_get_good_rule(self):
        # GET good rule 12345
        resp = requests.get(RESTURL + "/rest/rule/12345").json()
        print(resp)
        self.assertEqual(resp.get("success"), True)
        self.assertEqual(resp.get("id"), "12345")

    def test_6_get_all_rules(self):
        # Add another rule
        rule54321 = copy.deepcopy(self.rule12345)
        rule54321["data"]["id"] = "54321"
        resp = requests.put(RESTURL + "/rest/rule", json=rule54321).json()
        print(resp)
        self.assertEqual(resp.get("success"), True)
        self.assertEqual(resp.get("id"), "54321")
        # Get rules and make sure they are correct
        resp = requests.get(RESTURL + "/rest/rules").json()
        print(resp)
        self.assertEqual(len(resp["data"]), 2)
        for rule in resp["data"]:
            # if "123456" in rule["id"]:
            self.assertIn(rule["id"], ["12345", "54321"])

    def test_7_delete_good_rule(self):
        # DELETE existing rule 12345
        for rule_id in ["12345", "54321"]:
            resp = requests.delete(RESTURL + "/rest/rule/{}".format(rule_id)).json()
            print(resp)
            self.assertEqual(resp.get("success"), True)
            self.assertEqual(resp.get("id"), rule_id)

    def test_8_delete_missing_rule(self):
        # DELETE missing rule 4545
        # curl -X DELETE ${BASEURL}/rest/rule/4545
        resp = requests.delete(RESTURL + "/rest/rule/4545").json()
        print(resp)
        self.assertEqual(resp.get("success"), False)
        self.assertEqual(resp.get("id"), "4545")

    def test_9_load_rules_from_dir(self):
        mydir = os.path.dirname(__file__)
        json_test_rules_dir = os.path.join(mydir, "../json_test_rules")

        for file in os.listdir(json_test_rules_dir):
            self._load_test_json_file(file, json_test_rules_dir)

        # Reload rules to clear out past rules
        restapi_helpers.reload_rules(self, RESTURL)

    def test_A_load_realworld_rules_from_dir(self):
        mydir = os.path.dirname(__file__)
        json_test_rules_dir = os.path.join(mydir, "../json_realworld_rules")

        for file in os.listdir(json_test_rules_dir):
            self._load_test_json_file(file, json_test_rules_dir)

        # Reload rules to clear out past rules
        restapi_helpers.reload_rules(self, RESTURL)

    def _load_test_json_file(self, file, rules_dir):

        if file.endswith("json"):
            print()
            filename = os.path.join(rules_dir, file)
            print("Found rule file: {}".format(filename))

            try:
                json_rule = json.load(open(filename))
            except Exception as e:
                print("Error loading rule file: {}".format(str(e)))
            self.assertIsNotNone(json_rule)

            rule_id = json_rule["id"]
            restapi_helpers.put_rule(self, RESTURL, json_rule)
            restapi_helpers.reload_rules(self, RESTURL)
            restapi_helpers.get_rule(self, RESTURL, rule_id)
            restapi_helpers.delete_rule(self, RESTURL, rule_id)


if __name__ == "__main__":
    unittest.main()
