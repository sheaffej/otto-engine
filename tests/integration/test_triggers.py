#!/usr/bin/env python3

import asyncio
import asyncws
import datetime
import requests
import json
import unittest

WSHOST = "localhost"
WSPORT = 8000
RESTHOST = "localhost"
RESTPORT = 5000

WSURL = "ws://{}:{}".format(WSHOST, WSPORT)
RESTURL = "http://{}:{}".format(RESTHOST, RESTPORT)


class TestTriggers(unittest.TestCase):

    def setUp(self):
        print()

    def tearDown(self):
        pass

    def test_state_changed(self):
        async def _state_changed():

            # Register the rule
            rule_id = "12345"

            # Trigger
            trig_entity_id = "input_boolean.test"
            trig_old_state = "off"
            trig_new_state = "on"

            # Action
            act_entity_id = "input_boolean.action_light"
            act_service = "turn_on"
            rule = {
                "data": {
                    "id": rule_id,
                    "description": "Test Rule",
                    "enabled": True,
                    "group": "Testing",
                    "triggers": [
                        {
                            "platform": "state",
                            "entity_id": trig_entity_id,
                            "to": trig_new_state,
                            "from": trig_old_state
                        },
                    ],
                    "actions": [
                        {
                            "action_sequence": [
                                {
                                    "domain": "input_boolean",
                                    "service": act_service,
                                    "data": {
                                        "entity_id": act_entity_id
                                    }
                                }
                            ]
                        }
                    ]
                }
            }

            resp = requests.put(RESTURL + "/rest/rule", json=rule).json()
            print(resp)
            self.assertEqual(resp.get("success"), True)
            self.assertEqual(resp.get("id"), rule_id)

            resp = requests.get(RESTURL + "/rest/reload").json()
            print(resp)
            self.assertEqual(resp.get("success"), True)

            websocket = await asyncws.connect(WSURL)

            now = datetime.datetime.now()
            event = {
                "id": 1,
                "type": "event",
                "event": {
                    "event_type": "state_changed",
                    "data": {
                        "entity_id": trig_entity_id,
                        "old_state": {
                            "entity_id": trig_entity_id,
                            "state": trig_old_state,
                            "attributes": {},
                            "last_changed": (now - datetime.timedelta(minutes=15)).isoformat(),
                            "last_updated": (now - datetime.timedelta(minutes=15)).isoformat()
                        },
                        "new_state": {
                            "entity_id": trig_entity_id,
                            "state": trig_new_state,
                            "attributes": {},
                            "last_changed": now.isoformat(),
                            "last_updated": now.isoformat()
                        }
                    },
                    "origin": "LOCAL",
                    "time_fired": now.isoformat()
                }
            }
            await websocket.send(json.dumps(event))

            resp = await websocket.recv()
            resp = json.loads(resp)
            print(resp)

            self.assertEqual(resp.get("type"), "call_service")
            self.assertEqual(resp.get("domain"), "input_boolean")
            self.assertEqual(resp.get("service"), act_service)
            self.assertEqual(resp.get("service_data").get("entity_id"), act_entity_id)

            await websocket.close()

            resp = requests.delete(RESTURL + "/rest/rule/{}".format(rule_id)).json()
            print(resp)
            self.assertEqual(resp.get("success"), True)
            self.assertEqual(resp.get("id"), rule_id)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_state_changed())


if __name__ == "__main__":
    unittest.main()
