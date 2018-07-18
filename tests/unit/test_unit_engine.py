#!/usr/bin/env python

import asyncio
import os
import unittest

from ottoengine import engine, config, enginelog, persistence
from ottoengine.utils import setup_debug_logging
from ottoengine.fibers import clock

setup_debug_logging()


class TestEngine(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestEngine, self).__init__(*args, **kwargs)
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
        setup_debug_logging()
        mydir = os.path.dirname(__file__)
        self.test_rules_dir = os.path.join(mydir, "../json_test_rules")
        self.realworld_rules_dir = os.path.join(mydir, "../json_realworld_rules")

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

    def test_check_timespec_success(self):
        tests = [
            {'tz': 'America/Los_Angeles'},
            {'blah': 'blah', 'tz': 'America/Los_Angeles'},
        ]
        for test in tests:
            result = self.engine_obj.check_timespec_threadsafe(test)
            print(test, "-->", result)
            self.assertTrue("success" in result)
            self.assertEquals(result.get("success"), True)

    def test_check_timespec_failure(self):
        tests = [
            {},                           # Missing mandatory tz attribute
            {'tz': 'utc', 'hour': "one"}  # "one" should be numeric 1
        ]
        for test in tests:
            result = self.engine_obj.check_timespec_threadsafe(test)
            print(test, "-->", result)
            self.assertTrue("success" in result)
            self.assertEquals(result.get("success"), False)

    def test_async_load_rules(self):
        cfg = config.EngineConfig()
        cfg.json_rules_dir = self.test_rules_dir
        self._setup_engine(config_obj=cfg)

        self.loop.run_until_complete(self.engine_obj._async_load_rules())


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """ This simply wraps the asyncio function so we have typing for autocomplet/linting"""
    return asyncio.get_event_loop()


if __name__ == "__main__":
    unittest.main()
