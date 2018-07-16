#!/usr/bin/env python
import unittest

from ottoengine import enginelog


class TestEnginelog(unittest.TestCase):

    def setUp(self):
        print()

    def test_log_retention(self):
        max_logs = 20
        print("Creating enginelog with max_logs = ", max_logs)
        enlog = enginelog.EngineLog(max_logs=max_logs)

        # Test log holds all entires when not filled
        num_add_logs = max_logs - 5
        logs = _fill_logs(enlog, num_add_logs)
        self.assertEqual(len(logs), num_add_logs)

        # Test log holds only max_logs when over filled
        num_add_logs = max_logs + 5
        logs = _fill_logs(enlog, num_add_logs)
        self.assertEqual(len(logs), max_logs)

        # Test log holds exactly max_logs when same number are added
        num_add_logs = max_logs
        logs = _fill_logs(enlog, num_add_logs)
        self.assertEqual(len(logs), num_add_logs)

    def test_zero_max_logs(self):
        # Test if max_logs is set to zero
        max_logs = 0
        print("Creating enginelog with max_logs = ", max_logs)
        enlog = enginelog.EngineLog(max_logs=max_logs)

        logs = _fill_logs(enlog, 10)
        self.assertEqual(len(logs), 0)

    def test_resize_log(self):
        max_logs_1 = 20
        print("Creating enginelog with max_logs = ", max_logs_1)
        enlog = enginelog.EngineLog(max_logs=max_logs_1)

        # Overfill first
        logs = _fill_logs(enlog, max_logs_1 + 7)
        self.assertEqual(len(logs), max_logs_1)

        # Then increase the size of the log: should have same number of logs
        max_logs_2 = max_logs_1 + 10
        enlog.set_max_logs(max_logs_2)
        logs = enlog.get_logs()
        self.assertAlmostEqual(len(logs), max_logs_1)

        # Then decrease the size of the log smaller than initial logs
        # The log should trim to the new max_log size
        max_logs_3 = max_logs_1 - 10
        enlog.set_max_logs(max_logs_3)
        logs = enlog.get_logs()
        self.assertAlmostEqual(len(logs), max_logs_3)


def _fill_logs(enlog: enginelog.EngineLog, num_add_logs: int) -> int:
    for i in range(num_add_logs):
        enlog.add(enginelog.DEBUG, {"idx": i})
    return enlog.get_logs()


if __name__ == "__main__":
    unittest.main()
