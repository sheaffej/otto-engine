#!/usr/bin/env python

import asyncio
import datetime
from dateutil import parser
import pytz
import unittest
import uuid

from ottoengine.fibers import clock
from ottoengine.helpers import nowutc

TZ = "America/Los_Angeles"


class TestClock(unittest.TestCase):

    def setUp(self):
        print()
        self.loop = asyncio.get_event_loop()
        self.engine = None
        self.clock = clock.EngineClock(TZ, loop=self.loop)

    def test_basic_tick(self):
        """Test the tick mechanism, to ensure it executes a TimeSpec at the right time.
        """
        trig = {
            "tz": TZ
        }
        nowtime = parser.parse("2018-05-08 21:38:00-00:00")
        spec = clock.TimeSpec.from_dict(trig)
        nexttime = spec.next_time_from(nowtime)

        print("nowtime: {}".format(nowtime.astimezone(pytz.timezone(TZ))))
        print("TimeSpec: {}".format(spec.serialize()))
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

    def test_remove_action(self):
        """Tests the removal of a TimeSpec from the timeline
        """

        async def _noop():
            pass

        spec = clock.TimeSpec.from_dict({"tz": "UTC"})
        spec_id = uuid.uuid4()
        self.clock.add_timespec_action(
            id=spec_id,
            action_function=_noop,
            timespec=spec,
            nowtime=nowutc()
        )

        # Add the TimeSpecAction
        self.assertEqual(len(self.clock.timeline), 1)
        actual_id = self.clock.timeline[0].actions[0].id
        print("Expected: {}, Actual: {}".format(spec_id, actual_id))
        self.assertEqual(actual_id, spec_id)

        # Remove the TimeSpecAction
        self.clock.remove_timespec_action(spec_id)
        print(self.clock._format_timeline())
        self.assertEqual(
            len(self.clock.timeline), 0,
            msg="Expecing an empty timeline, but it found non-empty")


class TestTimeSpec(unittest.TestCase):
    def setUp(self):
        print()

    def test_next_time_from(self):
        """Tests various TimeSpec definitions to ensure they calculate the correct next time
        """
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

            # Only July 4th at 9:30am
            ({"tz": "UTC", "second": 0, "minute": 30, "hour": 9, "day_of_month": 4, "month": 7},
             parser.parse("2018-01-01 00:00:00-00:00"), parser.parse("2018-07-04 09:30:00-00:00")),

            # Only Fri, Sat, Sun at 8:30a
            ({"tz": "UTC", "second": 0, "minute": 30, "hour": 8, "weekdays": "5,6,7"},
             parser.parse("2018-01-01 00:00:00-00:00"), parser.parse("2018-01-05 08:30:00-00:00")),
            ({"tz": "UTC", "second": 0, "minute": 30, "hour": 8, "weekdays": "5,6,7"},
             parser.parse("2018-01-05 08:30:01-00:00"), parser.parse("2018-01-06 08:30:00-00:00")),
            ({"tz": "UTC", "second": 0, "minute": 30, "hour": 8, "weekdays": "5,6,7"},
             parser.parse("2018-01-06 08:30:01-00:00"), parser.parse("2018-01-07 08:30:00-00:00")),
            ({"tz": "UTC", "second": 0, "minute": 30, "hour": 8, "weekdays": "5,6,7"},
             parser.parse("2018-01-07 08:30:01-00:00"), parser.parse("2018-01-12 08:30:00-00:00")),

            # Midnight UTC
            ({"tz": "UTC", "hour": 0, "minute": 0, "second": 0},
             parser.parse("2018-05-15 08:01:10-00:00"), parser.parse("2018-05-16 00:00:00-00:00")),
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
