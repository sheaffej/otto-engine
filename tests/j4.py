#!/usr/bin/env python

import asyncio
import clock
import datetime
# import pytz
import uuid
import logging
import sys

import config

LOG_LEVEL = logging.DEBUG

def setup_logging() -> None:
    """Setup the logging."""
    logging.basicConfig(level=LOG_LEVEL)
    fmt = ("%(asctime)s %(levelname)s (%(threadName)s) [%(name)s - %(funcName)s()] %(message)s")
    colorfmt = "%(log_color)s{}%(reset)s".format(fmt)
    datefmt = '%y-%m-%d %H:%M:%S'

    try:
        from colorlog import ColoredFormatter
        logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
            colorfmt,
            datefmt=datefmt,
            reset=True,
            log_colors={
                'DEBUG': 'blue',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        ))
    except ImportError:
        print("Failed to import colorlog module")
        sys.exit(1)

setup_logging()




# TZ="America/Los_Angels"

# TZ = pytz.timezone("America/Los_Angeles")

triggers = []

# triggers.append({
#     "is_utc": False,
#     "second": 0,
#     "minute": 30,
#     "hour": 18
# })

# triggers.append({
#     "is_utc": False,
#     "second": 0,
#     "minute": 30,
#     "hour": 9,
#     "day_of_month": 4,
#     "month": 7
# })

# triggers.append({
#     "is_utc": False,
#     "second": 0,
#     "minute": 30,
#     "hour": 8,
#     "weekdays": "5,6,7"
# })

# triggers.append({
#     "is_utc": False,
#     "second": 0,
#     "minute": 30,
#     "hour": 8,
#     "weekdays": "5,6,7"
# })

# Midnight UTC
# triggers.append({
#     "is_utc": True,
#     "hour": 0
# })
# triggers.append({
#     "is_utc": True,
#     "hour": 0
# })
# triggers.append({
#     "is_utc": True,
#     "hour": 0
# })
# triggers.append({
#     "is_utc": True,
#     "hour": 0
# })

triggers.append({
    "tz": config.TZ,
})

triggers.append({
    "tz": "UTC",
    "minute": "*/2"
})

triggers.append({
    "tz": config.TZ,
    "minute": "*/3"
})

loop = asyncio.get_event_loop()
engine_clock = clock.EngineClock(loop=loop)

print()
print("Now: {}".format(datetime.datetime.now()))

for trig in triggers:
    print()
    spec = clock.TimeSpec.from_dict(trig)
    print(spec.serialize())

    print ("--> next_time_from_now()")
    print(spec.next_time_from_now())

    id = uuid.uuid4()

    async def myfunc():
        print("Action executed: {}".format(id))

    engine_clock.add_timespec_action(id, myfunc, spec)

loop.create_task(engine_clock.async_run())
loop.run_forever()


# TODO:
# x Implement TimeTrigger
# - Extend AutomationRule or OttoEngine to handle TimeTriggers
#   -> engine.py:  107
#   -> rule_objects: 42
# - Implement remove AlarmAction
