#!/usr/bin/env python

# import asyncio
import unittest

from ottoengine import engine, config


class TestEngine(unittest.TestCase):
    def setUp(self):
        print()
        # self.loop = asyncio.get_event_loop()
        self.config = config.EngineConfig()
        self.engine = engine.OttoEngine(self.config)

    def test_check_timespec(self):
        tests = [
            {'platform': 'time', 'tz': 'America/Los_Angeles'}
        ]
        for test in tests:
            result = self.engine.check_timespec(test)
            self.assertTrue("success" in result)
            self.assertEquals(result.get("success"), True)


if __name__ == "__main__":
    unittest.main()
