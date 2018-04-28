import datetime
import pytz

def timedelta_to_dict(delta: datetime.timedelta) -> dict:
    return {
        "days": delta.days,
        "secs": delta.seconds,
        "ms": delta.microseconds
    }

def time_to_dict(time_obj: datetime.time) -> dict:
    return {
        "hours": time_obj.hour,
        "mins": time_obj.minute,
        "secs": time_obj.second,
        "ms": time_obj.microsecond
    }

def dict_to_timedelta(delta_dict) -> datetime.timedelta:
    days = delta_dict.get('days', 0)
    secs = delta_dict.get('secs', 0)
    ms = delta_dict.get('ms', 0)
    return datetime.timedelta(days, secs, ms)

def dict_to_time(time_dict) -> datetime.time:
    hours = time_dict.get('hours', 0)
    mins = time_dict.get('mins', 0)
    secs = time_dict.get('secs', 0)
    us = time_dict.get('us', 0)
    return datetime.time(hour=hours, minute=mins, second=secs, microsecond=us)

def hms_string_to_timedelta(hms_string) -> datetime.timedelta:
    if hms_string is None:
        return None
    parts = [int(s) for s in hms_string.split(":")]
    secs = (parts[0] * (3600)) + (parts[1] * 60) + parts[2]
    return datetime.timedelta(0, secs, 0)

def hms_string_to_time(hms_string, tz_name) -> datetime.time:
    # 00:00:00
    if hms_string is None:
        return None
    parts = [int(s) for s in hms_string.split(":")]
    # secs = (parts[0] * (3600)) + (parts[1] * 60) + parts[2]
    # return datetime.timedelta(0, secs, 0)
    return datetime.time(hour=parts[0], minute=parts[1], second=parts[2], tzinfo=pytz.timezone(tz_name))


def time_to_hms_string(time_obj:datetime.time) -> str:
    if time_obj is None:
        return None;
    return "{:02d}:{:02d}:{:02d}".format(time_obj.hour, time_obj.minute, time_obj.second)


def timedelta_to_hms_string(delta: datetime.timedelta) -> str:
    m, s = divmod(delta.seconds, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02d" % (h, m, s)

def day_of_week_xxx(datetime: datetime.datetime) -> str:
    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    return days[datetime.weekday()]


class ValidationError(Exception):
    """Exception class for improperly constructed objects"""
    def __init__(self, message):
        super().__init__(message)

