#!/usr/bin/env python

import asyncio
import datetime as dt
import logging
import os
import pytz
import unittest

from ottoengine import engine as engine_mod, enginelog as enginelog_mod
from ottoengine import persistence, helpers
from ottoengine.utils import setup_logging
from ottoengine.fibers import clock as clock_mod
from ottoengine.model.dataobjects import EntityState

tz_name = "America/Los_Angeles"
setup_logging(logging.DEBUG)
_LOG = logging.getLogger(__name__)


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

    def setUp(self):
        print()
        mydir = os.path.dirname(__file__)
        self.test_rules_dir = os.path.join(mydir, "../json_test_rules")
        self.realworld_rules_dir = os.path.join(mydir, "../json_realworld_rules")
        self.loop = get_event_loop()

        # Monkey patch nowutc() so we can control the exact time
        self.sim_time = dt.datetime.now(pytz.utc)  # Set a type for linting/ac
        helpers.nowutc = lambda: self.sim_time

    def test_2764351_away_lights(self):
        rule_id = "2764351"

        # Setup OttoEngine for testing
        config = None
        loop = None
        clock = clock_mod.EngineClock(tz_name, loop=self.loop)
        persistence_mgr = persistence.PersistenceManager(self.realworld_rules_dir)
        enginelog = enginelog_mod.EngineLog()
        engine_obj = engine_mod.OttoEngine(config, loop, clock, persistence_mgr, enginelog)
        engine_obj._websocket = MockWebSocketClient()

        # Set the simulation time
        local_tz = pytz.timezone(tz_name)
        self.sim_time = local_tz.localize(dt.datetime(2018, 7, 14, 0, 0, 00))

        # ~~~~~~~~~~~~~
        # Load the rule
        # ~~~~~~~~~~~~~
        filename = os.path.join(self.realworld_rules_dir, "{}.json".format(rule_id))
        rule = persistence_mgr.load_rule_from_file(filename)
        print(rule.serialize())
        self.assertEqual(rule.id, rule_id)
        self.loop.run_until_complete(engine_obj._async_load_rule(rule))

        # Verify rule loaded properly
        print("Engine state should only have the one rule loaded")
        state_rules = engine_obj.states.get_rules()
        self.assertEqual(len(state_rules), 1)
        self.assertEqual(state_rules[0].id, rule.id)
        print("Clock should have two ClockAlarms defined on the timeline")
        self.assertEqual(len(clock.timeline), 2)
        for l in clock.timeline:
            print("Engine has ClockAlarm at:", str(l.alarm_time))

        # ~~~~~~~~~~~~~
        # Set pre-state
        # ~~~~~~~~~~~~~
        vacation_mode_state = EntityState(
            "input_boolean.vacation_mode",
            "on",
            {},
            self.sim_time
        )
        engine_obj.states.set_entity_state(vacation_mode_state.entity_id, vacation_mode_state)
        self.assertEqual(
            engine_obj.states.get_entity_state(vacation_mode_state.entity_id).state,
            vacation_mode_state.state)

        # ~~~~~~~~~~~~~~~~~
        # Trigger lights on
        # ~~~~~~~~~~~~~~~~~
        self.sim_time = local_tz.localize(dt.datetime(2018, 7, 14, 19, 21, 00))
        print("Running sim at: ", str(helpers.nowutc()))
        self.loop.run_until_complete(clock._async_tick(self.sim_time))

        # Check that the correct service was called
        wscalls = engine_obj._websocket.service_calls
        self.assertEqual(len(wscalls), 1)
        self.assertEqual(wscalls[0].service, "turn_on")
        self.assertEqual(wscalls[0].service_data.get("entity_id"), "scene.living_room_bright")
        engine_obj._websocket.clear()

        # ~~~~~~~~~~~~~~~~~~
        # Trigger lights off
        # ~~~~~~~~~~~~~~~~~~
        self.sim_time = local_tz.localize(dt.datetime(2018, 7, 14, 22, 7, 00))
        print("Running sim at: ", str(helpers.nowutc()))
        self.loop.run_until_complete(clock._async_tick(self.sim_time))

        # Check that the correct service was called
        wscalls = engine_obj._websocket.service_calls
        self.assertEqual(len(wscalls), 1)
        self.assertEqual(wscalls[0].service, "turn_on")
        self.assertEqual(wscalls[0].service_data.get("entity_id"), "scene.all_lights_off")
        engine_obj._websocket.clear()


def get_event_loop() -> asyncio.AbstractEventLoop:
    """ This simply wraps the asyncio function so we have typing for autocomplet/linting"""
    return asyncio.get_event_loop()


if __name__ == "__main__":
    unittest.main()
