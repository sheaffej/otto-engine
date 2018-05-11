#!/usr/bin/env python

import asyncio
import datetime
from dateutil import parser
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


class TestTimeSpec(unittest.TestCase):
    def setUp(self):
        print()

    def test_next_time_from(self):
        # (TimeSpec, nowtime, nexttime)
        tests = [
            ({"tz": "UTC"},
             parser.parse("2018-01-01 00:00:00-00:00"), parser.parse("2018-01-01 00:01:00-00:00")),

            ({"tz": "UTC", "minute": "*/2"},
             parser.parse("2018-01-01 00:00:00-00:00"), parser.parse("2018-01-01 00:02:00-00:00")),
            ({"tz": "UTC", "minute": "*/2"},
             parser.parse("2018-01-01 00:01:59-00:00"), parser.parse("2018-01-01 00:02:00-00:00")),
            ({"tz": "UTC", "minute": "*/2"},
             parser.parse("2018-12-31 23:59:59-00:00"), parser.parse("2019-01-01 00:00:00-00:00")),

            ({"tz": "UTC", "minute": "*/3"},
             parser.parse("2018-01-01 00:00:00-00:00"), parser.parse("2018-01-01 00:03:00-00:00")),
            ({"tz": "UTC", "minute": "*/3"},
             parser.parse("2018-01-01 00:02:59-00:00"), parser.parse("2018-01-01 00:03:00-00:00")),
            ({"tz": "UTC", "minute": "*/3"},
             parser.parse("2018-12-31 23:59:59-00:00"), parser.parse("2019-01-01 00:00:00-00:00")),
            ({"tz": "UTC", "minute": "*/3"},
             parser.parse("2018-01-01 00:00:01-00:00"), parser.parse("2018-01-01 00:03:00-00:00")),

            ({"tz": "UTC", "second": 0, "minute": 30, "hour": 18},
             parser.parse("2018-01-01 00:00:00-00:00"), parser.parse("2018-01-01 18:30:00-00:00")),
            ({"tz": "UTC", "second": 0, "minute": 30, "hour": 18},
             parser.parse("2018-01-01 18:30:01-00:00"), parser.parse("2018-01-02 18:30:00-00:00")),
            ({"tz": "UTC", "second": 0, "minute": 30, "hour": 18},
             parser.parse("2018-12-31 18:30:01-00:00"), parser.parse("2019-01-01 18:30:00-00:00")),

            # Leap years
            ({"tz": "UTC"},
             parser.parse("2016-02-28 23:59:59-00:00"), parser.parse("2016-02-29 00:00:00-00:00")),
            ({"tz": "UTC"},
             parser.parse("2020-02-28 23:59:59-00:00"), parser.parse("2020-02-29 00:00:00-00:00")),
            ({"tz": "UTC"},
             parser.parse("2024-02-28 23:59:59-00:00"), parser.parse("2024-02-29 00:00:00-00:00")),

            # Not a leap year
            ({"tz": "UTC"},
             parser.parse("2018-02-28 23:59:59-00:00"), parser.parse("2018-03-01 00:00:00-00:00")),
        ]

        for specdict, nowtime, nexttime in tests:
            spec = clock.TimeSpec.from_dict(specdict)
            actualnext = spec.next_time_from(nowtime)
            print("TimeSpec: {}".format(spec.serialize()))
            print("Nowtime: {}".format(nowtime))
            print("Exected nexttime: {}, Actual: {}".format(nexttime, actualnext))
            self.assertEqual(
                actualnext, nexttime,
                msg="Spec: {}, Expected: {}, Actual: {}".format(
                    spec.serialize(), nexttime, actualnext)
            )


if __name__ == "__main__":
    unittest.main()
