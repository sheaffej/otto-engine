#!/usr/bin/env python

import asyncio
import datetime
import pytz
import unittest
import uuid

from ottoengine import clock

TZ = "America/Los_Angeles"


class TestClock(unittest.TestCase):

    def setUp(self):
        print()
        self.loop = asyncio.get_event_loop()
        self.clock = clock.EngineClock(TZ, loop=self.loop)

    def test_basic(self):
        trig = {
            "tz": TZ
        }

        nowtime = datetime.datetime(2018, 5, 8, hour=21, minute=38, second=0, tzinfo=pytz.utc)
        print("nowtime: {}".format(nowtime.astimezone(pytz.timezone(TZ))))

        spec = clock.TimeSpec.from_dict(trig)
        print("TimeSpec: {}".format(spec.serialize()))

        nexttime = spec.next_time_from(nowtime)
        print("nextime: {}".format(nexttime))

        self.action_count = 0
        self.exec_time = None

        async def myfunc():
            self.action_count += 1
            self.exec_time = nowtime
            print("Action executed at {}".format(self.exec_time))

        self.clock.add_timespec_action(uuid.uuid4(), myfunc, spec, nowtime)
        print(self.clock._format_timeline())

        for i in range(65):
            self.loop.run_until_complete(self.clock._async_tick(nowtime))
            nowtime = nowtime + datetime.timedelta(seconds=1)
            print("tick: {}".format(nowtime.astimezone(pytz.timezone(TZ))))

        self.assertEqual(self.action_count, 1)
        print(self.exec_time.astimezone(pytz.utc))
        print(nexttime.astimezone(pytz.utc))
        self.assertTrue(self.exec_time == nexttime)


if __name__ == "__main__":
    unittest.main()
