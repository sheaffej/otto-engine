#!/usr/bin/env python3

import asyncio
import asyncws
import json
import unittest

from ottoengine.testing.rule_helpers import AutomationRuleSpec
from ottoengine.trigger_objects import StateTrigger, NumericStateTrigger, EventTrigger
from ottoengine.action_objects import ServiceAction
from ottoengine.rule_objects import RuleAction
from ottoengine.testing import websocket_helpers, restapi_helpers


WSHOST = "localhost"
WSPORT = 8000
RESTHOST = "localhost"
RESTPORT = 5000

RULEGROUP = "Testing"
RULE_DESCRIPTION = "Test Rule"

WSURL = "ws://{}:{}".format(WSHOST, WSPORT)
RESTURL = "http://{}:{}".format(RESTHOST, RESTPORT)


class TestTriggers(unittest.TestCase):

    def setUp(self):
        print()
        self.act_domain = "input_boolean"
        self.act_entity_id = "input_boolean.action_light"
        self.act_service = "turn_on"
        self.action = ServiceAction(
            self.act_domain, self.act_service, entity_id=self.act_entity_id)

    def tearDown(self):
        pass

    def _basic_rule_helper(self, rule_id, trigger):
        """
            :rtype: AutomationRuleSpec
        """
        rulespec = AutomationRuleSpec(rule_id, RULEGROUP, description=RULE_DESCRIPTION)
        rulespec.add_trigger(trigger)
        action = RuleAction()
        action.action_sequence.append(self.action)
        rulespec.add_action(action)
        print("Rule spec: {}".format(rulespec.serialize()))
        return rulespec

    def _check_action_helper(self, response):
        """
            :param str response: The JSON string response from the websocket
            :rtype: None
        """
        resp = json.loads(response)
        print("Event response: {}".format(resp))
        self.assertEqual(resp.get("type"), "call_service")
        self.assertEqual(resp.get("domain"), "input_boolean")
        self.assertEqual(resp.get("service"), self.act_service)
        self.assertEqual(resp.get("service_data").get("entity_id"), self.act_entity_id)

    def test_state_changed_trigger(self):
        async def _state_changed():

            # Build the rule
            rule_id = "12345"
            trig_entity_id = "input_boolean.test"
            trig_old_state = "off"
            trig_new_state = "on"

            trigger = StateTrigger(trig_entity_id, to_state="on", from_state="off")
            rulespec = self._basic_rule_helper(rule_id, trigger)

            # Send the rule
            restapi_helpers.put_rule(self, RESTURL, rulespec)
            restapi_helpers.reload_rules(self, RESTURL)

            # Send the event
            websocket = await asyncws.connect(WSURL)
            event = websocket_helpers.event_state_changed(
                1, trig_entity_id, trig_old_state, trig_new_state)
            await websocket.send(json.dumps(event))

            # Check the resulting action
            response = await websocket.recv()
            self._check_action_helper(response)

            # Clean up
            await websocket.close()
            restapi_helpers.delete_rule(self, RESTURL, rule_id)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_state_changed())

    def test_numeric_state_trigger(self):
        async def _numeric_state():
            # Build the rule
            rule_id = "12345"

            trig_entity_id = "input_boolean.test"
            trig_above_val = 1
            trig_below_val = 10
            event_old_val = 0
            event_new_val = 5

            trigger = NumericStateTrigger(
                    trig_entity_id, above_value=trig_above_val, below_value=trig_below_val)
            rulespec = self._basic_rule_helper(rule_id, trigger)

            # Send the rule
            restapi_helpers.put_rule(self, RESTURL, rulespec)
            restapi_helpers.reload_rules(self, RESTURL)

            # Send the event
            websocket = await asyncws.connect(WSURL)
            event = websocket_helpers.event_state_changed(
                1, trig_entity_id, event_old_val, event_new_val)
            await websocket.send(json.dumps(event))

            response = await websocket.recv()
            self._check_action_helper(response)

            # Clean up
            await websocket.close()
            restapi_helpers.delete_rule(self, RESTURL, rule_id)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_numeric_state())

    def test_event_trigger(self):
        async def _event():
            # Build the rule
            rule_id = "12345"

            trig_event_type = "timer_ended"
            trig_event_data = {"timer": "main_light"}

            trigger = EventTrigger(trig_event_type, trig_event_data)
            rulespec = self._basic_rule_helper(rule_id, trigger)

            # Send the rule
            restapi_helpers.put_rule(self, RESTURL, rulespec)
            restapi_helpers.reload_rules(self, RESTURL)

            # Send the event
            websocket = await asyncws.connect(WSURL)
            event = websocket_helpers.event_hass_event(rule_id, trig_event_type, trig_event_data)
            await websocket.send(json.dumps(event))

            response = await websocket.recv()
            self._check_action_helper(response)

            # Clean up
            await websocket.close()
            restapi_helpers.delete_rule(self, RESTURL, rule_id)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_event())

    # Note: TimeTrigger is tested differently as it's triggered by the EngineClock and not by
    # Home Assistant events.

    # This test also tests the ServiceAction, which is the only Action that integrates with
    # Home Assistant. The remaining actions: LogAction, DelayAction, ConditionAction all
    # stay within the Otto Engine.

if __name__ == "__main__":
    unittest.main()
