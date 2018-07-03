#!/usr/bin/env python

from dateutil.parser import parse
# import pytz
import unittest

from ottoengine.model import condition_objects

PT_TZ = 'America/Los_Angeles'


class TestConditionObjects(unittest.TestCase):

    def setUp(self):
        print()

    def test_time_condition(self):
        # (
        #   condition_dict, condition_tz,
        #   evaltime, expected True/False/Exception
        # )
        tests = [
            (   # PT condition w/ PT evaltime: eval True
                {"condition": "time", "after": "09:00:00", "before": "10:00:00", "tz": PT_TZ},
                parse("2018-01-01 09:10:00-08:00"), True
            ),
            (   # PT condition w/ PT evaltime: eval False
                {"condition": "time", "after": "09:00:00", "before": "10:00:00", "tz": PT_TZ},
                parse("2018-01-01 10:10:00-08:00"), False
            ),
            (   # PT condition w/ UTC evaltime: eval True
                {"condition": "time", "after": "09:00:00", "before": "10:00:00", "tz": PT_TZ},
                parse("2018-07-01 16:10:00-00:00"), True
            ),
            (   # PT condition w/ UTC evaltime: eval False
                {"condition": "time", "after": "09:00:00", "before": "10:00:00", "tz": PT_TZ},
                parse("2018-01-01 09:10:00-00:00"), False
            ),

            (   # Weekday Test: eval True
                {"condition": "time", "after": "09:00:00", "tz": PT_TZ,
                    "weekday": ["mon", "wed", "fri"]},
                parse("2018-07-02 09:10:00-07:00"), True
            ),
            (   # Weekday Test: eval False
                {"condition": "time", "after": "09:00:00", "tz": PT_TZ,
                    "weekday": ["mon", "wed", "fri"]},
                parse("2018-07-03 09:10:00-07:00"), False
            ),
            (   # Weekday Test, UTC day after PT day: eval True
                {"condition": "time", "after": "19:00:00", "tz": PT_TZ,
                    "weekday": ["sat"]},
                parse("2018-06-03 02:10:00-00:00"), True
            ),
            (   # Weekday Test, UTC day after PT day: eval False
                {"condition": "time", "after": "19:00:00", "tz": PT_TZ,
                    "weekday": ["sat"]},
                parse("2018-06-02 02:10:00-00:00"), False
            ),

            (   # Test only if weekday is in condtion: eval True
                {"condition": "time", "tz": PT_TZ,
                    "weekday": ["sat"]},
                parse("2018-06-30 02:10:00-07:00"), True
            ),

            # Test invalid conditions: eval False
            (
                {"condition": "time", "tz": PT_TZ},
                parse("2018-06-30 02:10:00-07:00"), TypeError()
            ),
            (
                {"condition": "time"},
                parse("2018-06-30 02:10:00-07:00"), TypeError()
            ),
        ]

        for cond_dict, evaltime, expected in tests:
            print()
            print("cond_dict: ", cond_dict)
            try:
                cond_obj = condition_objects.TimeCondition.from_dict(cond_dict)
                print("cond_obj: {}".format(cond_obj.serialize()))
                print("evaltime:", evaltime)
                print("expected:", expected)
                result = cond_obj.evaluate_at(evaltime)
                print("Actual: ", result)
                self.assertEqual(result, expected)
            except Exception as e:
                print("Exception raised:", type(e), e)
                if isinstance(expected, Exception):
                    self.assertIsInstance(e, type(expected))
                else:
                    self.fail(
                        msg="Exception {} raised when expecting {}".format(type(e), type(expected)))


if __name__ == "__main__":
    unittest.main()
