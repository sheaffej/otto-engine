#!/usr/bin/env python3
import requests
import unittest

RESTURL = "http://localhost:5000"


class TestRulePersistence(unittest.TestCase):

    def __init__(self, *args):
        super(TestRulePersistence, self).__init__(*args)

        self.rule12345 = {
            "data": {
                "id": "12345",
                "description": "Turn everything on after a 3 second delay if both triggered",
                "enabled": True,
                "group": "Test",
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

    # def test_dummy(self):
    #     self.assertEqual(1, 1)

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
        resp = requests.put(RESTURL + "/rest/rule/4545", json=self.rule12345).json()
        print(resp)
        self.assertEqual(resp.get("success"), True)
        self.assertEqual(resp.get("id"), "12345")

    def test_5_get_good_rule(self):
        # GET good rule 12345
        # curl -X GET ${BASEURL}/rest/rule/12345
        resp = requests.get(RESTURL + "/rest/rule/12345").json()
        print(resp)
        self.assertEqual(resp.get("success"), True)
        self.assertEqual(resp.get("id"), "12345")

    def test_6_delete_good_rule(self):
        # DELETE existing rule 12345
        # curl -X DELETE ${BASEURL}/rest/rule/12345
        resp = requests.delete(RESTURL + "/rest/rule/12345").json()
        print(resp)
        self.assertEqual(resp.get("success"), True)
        self.assertEqual(resp.get("id"), "12345")

    def test_7_delete_missing_rule(self):
        # DELETE missing rule 4545
        # curl -X DELETE ${BASEURL}/rest/rule/4545
        resp = requests.delete(RESTURL + "/rest/rule/4545").json()
        print(resp)
        self.assertEqual(resp.get("success"), False)
        self.assertEqual(resp.get("id"), "4545")


if __name__ == "__main__":
    unittest.main()
