#!/usr/bin/env python

import asyncio
import datetime as dt
import os
import pytz
import unittest

from ottoengine import config, engine, enginelog
from ottoengine import persistence, helpers
from ottoengine.utils import setup_debug_logging
from ottoengine.fibers import clock, hass_websocket_reader
from ottoengine.testing import websocket_helpers

tz_name = "America/Los_Angeles"
setup_debug_logging()


class MockWebSocketClient():
    def __init__(self):
        self.service_calls = []

    async def async_call_service(self, service_call_info):
        print("Websocket async_call_service called with: {}".format(
            service_call_info.serialize()))
        self.service_calls.append(service_call_info)

    def clear(self):
        self.service_calls = []


class TestRuleProcessing(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestRuleProcessing, self).__init__(*args, **kwargs)
        # Initialize with defaults and to enable linting/ac
        # Test should call _setup_engine() to override any of these attributes
        self.loop = _get_event_loop()
        self.config = config.EngineConfig()
        self.clock = clock.EngineClock(self.config.tz, self.loop)
        self.persist_mgr = persistence.PersistenceManager(self.config.json_rules_dir)
        self.enlog = enginelog.EngineLog()
        self.engine_obj = engine.OttoEngine(
            self.config, self.loop, self.clock, self.persist_mgr, self.enlog)

    def setUp(self):
        print()
        mydir = os.path.dirname(__file__)
        self.test_rules_dir = os.path.join(mydir, "../json_test_rules")
        self.realworld_rules_dir = os.path.join(mydir, "../json_realworld_rules")

    # ~~~~~~~~~
    #  Helpers
    # ~~~~~~~~~
    def _monkey_patch_nowutc(self):
        # Monkey patch nowutc() so we can control the exact time
        self.sim_time = dt.datetime.now(pytz.utc)  # Set a type for linting/ac
        helpers.nowutc = lambda: self.sim_time

    def _setup_engine(self, config_obj: config.EngineConfig = None,
                      loop: asyncio.AbstractEventLoop = None,
                      clock_obj: clock.EngineClock = None,
                      persist_mgr: persistence.PersistenceManager = None,
                      enlog: enginelog.EngineLog = None):
        # These have setup with defautls by the constructor but can be overridden
        # if they are supplied as arguments to this function
        if config_obj:
            self.config = config_obj
        if loop:
            self.loop = loop
        if clock_obj:
            self.clock = clock_obj
        if enlog:
            self.enlog = enlog
        if persist_mgr:
            self.persist_mgr = persistence.PersistenceManager(config.json_rules_dir)

        # Always recreate the engine object when this function is called
        self.engine_obj = engine.OttoEngine(
            self.config, self.loop, self.clock, self.persist_mgr, self.enlog)
        self.engine_obj._websocket = MockWebSocketClient()

    async def _load_one_rule(self, rule_id, json_dir):
        filename = os.path.join(json_dir, "{}.json".format(rule_id))
        persist_mgr = self.engine_obj._persistence_mgr
        rule = persist_mgr.load_rule_from_file(filename)
        self.assertEqual(rule.id, rule_id)
        await self.engine_obj._async_load_rule(rule)

        print("Engine state should only have the one rule loaded")
        state_rules = self.engine_obj.states.get_rules()
        self.assertEqual(len(state_rules), 1)
        self.assertEqual(state_rules[0].id, rule.id)
        return rule

    async def _set_and_verify_entity_state(self, entity_id: str,
                                           new_state: str, old_state: str):
        event = websocket_helpers.event_state_changed(1, entity_id, old_state, new_state)
        await hass_websocket_reader._process_event_response(self.engine_obj, event)
        self.assertEqual(
            self.engine_obj.states.get_entity_state(entity_id).state, new_state)

    def _verify_websocket_service_call(self, seq_id, entity_id, service_name):
        wscalls = self.engine_obj._websocket.service_calls
        self.assertEqual(wscalls[0].service_data.get("entity_id"), entity_id)
        self.assertEqual(wscalls[0].service, service_name)
        print("Websocket call is correct: [{}] {} {}".format(seq_id, entity_id, service_name))

    # ~~~~~~~
    #  Tests
    # ~~~~~~~
    def test_2764351_away_lights(self):
        rule_id = "2764351"
        cfg = config.EngineConfig()
        cfg.json_rules_dir = self.realworld_rules_dir
        self._setup_engine(config_obj=cfg)

        # Set the simulation time
        self._monkey_patch_nowutc()
        local_tz = pytz.timezone(tz_name)
        self.sim_time = local_tz.localize(dt.datetime(2018, 7, 14, 0, 0, 00))

        print("Loading the rule")
        self.loop.run_until_complete(
            self._load_one_rule(rule_id, self.realworld_rules_dir)
        )

        # Verify rule loaded properly
        print("Clock should have two ClockAlarms defined on the timeline")
        self.assertEqual(len(self.engine_obj._clock.timeline), 2)

        print("Setting the pre-state")
        self.loop.run_until_complete(
            self._set_and_verify_entity_state("input_boolean.vacation_mode", "on", "off"))

        print("Trigger lights on")
        self.sim_time = local_tz.localize(dt.datetime(2018, 7, 14, 19, 21, 00))
        print("Running sim at: ", str(helpers.nowutc()))
        self.loop.run_until_complete(self.engine_obj._clock._async_tick(self.sim_time))

        # Check that the correct service was called
        self._verify_websocket_service_call(0, "scene.living_room_bright", "turn_on")
        self.engine_obj._websocket.clear()

        print("Trigger lights off")
        self.sim_time = local_tz.localize(dt.datetime(2018, 7, 14, 22, 7, 00))
        print("Running sim at: ", str(helpers.nowutc()))
        self.loop.run_until_complete(self.engine_obj._clock._async_tick(self.sim_time))

        # Check that the correct service was called
        self._verify_websocket_service_call(0, "scene.all_lights_off", "turn_on")
        self.engine_obj._websocket.clear()

    def test_action_condition(self):
        rule_id = "action_condition"
        cfg = config.EngineConfig()
        cfg.json_rules_dir = self.test_rules_dir
        self._setup_engine(config_obj=cfg)

        # Set the simulation time
        self.sim_time = helpers.nowutc()

        print("Loading the rule")
        self.loop.run_until_complete(
            self._load_one_rule(rule_id, self.test_rules_dir)
        )

        print("Setting pre-state")
        self.loop.run_until_complete(
            self._set_and_verify_entity_state("input_boolean.action_light", "off", "on",))
        self.engine_obj._websocket.clear()

        print("Triggering rule")
        self.loop.run_until_complete(
            self._set_and_verify_entity_state("input_boolean.test", "on", "off",))

        # Check that the correct service was called
        self._verify_websocket_service_call(0, "input_boolean.action_light", "turn_on")
        self.engine_obj._websocket.clear()

    def test_rule_condition(self):
        rule_id = "rule_condition"
        cfg = config.EngineConfig()
        cfg.json_rules_dir = self.test_rules_dir
        self._setup_engine(config_obj=cfg)

        # Set the simulation time
        self.sim_time = helpers.nowutc()

        print("Loading the rule")
        self.loop.run_until_complete(
            self._load_one_rule(rule_id, self.test_rules_dir)
        )

        print("Setting pre-state")
        self.loop.run_until_complete(
            self._set_and_verify_entity_state("input_boolean.action_light", "off", "on",))
        self.engine_obj._websocket.clear()

        print("Triggering rule, rule should pass")
        self.loop.run_until_complete(
            self._set_and_verify_entity_state("input_boolean.test", "on", "off",))

        # Check that the correct service was called
        self._verify_websocket_service_call(0, "input_boolean.action_light", "turn_on")
        self.engine_obj._websocket.clear()

        # Update the light's state, since Home Assistant would respond to the service_call
        # with any state changed events
        self.loop.run_until_complete(
            self._set_and_verify_entity_state("input_boolean.action_light", "on", None))

        # Now that light is on, triggering input_boolean.test to on again
        # should not run the rule

        print("Turning off input_boolean.test, should not trigger rule")
        self.loop.run_until_complete(
            self._set_and_verify_entity_state("input_boolean.test", "off", "on",))
        self.assertEqual(len(self.engine_obj._websocket.service_calls), 0)

        print("Triggering again, but light is already on, rule should not run")
        self.loop.run_until_complete(
            self._set_and_verify_entity_state("input_boolean.test", "on", "off",))
        self.assertEqual(len(self.engine_obj._websocket.service_calls), 0)


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """ This simply wraps the asyncio function so we have typing for autocomplet/linting"""
    return asyncio.get_event_loop()


if __name__ == "__main__":
    unittest.main()
