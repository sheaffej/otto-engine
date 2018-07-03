import datetime
import pytz


def nowutc() -> datetime.datetime:
    return datetime.datetime.now(pytz.utc)


def timedelta_to_dict(delta) -> dict:
    """
        :param datetime.timedelta delta:
        :rtype: dict
    """
    return {
        "days": delta.days,
        "secs": delta.seconds,
        "ms": delta.microseconds
    }


def time_to_dict(time_obj) -> dict:
    """
        :param datetime.time time_obj:
        :rtype: dict
    """
    return {
        "hours": time_obj.hour,
        "mins": time_obj.minute,
        "secs": time_obj.second,
        "ms": time_obj.microsecond
    }


def dict_to_timedelta(delta_dict) -> datetime.timedelta:
    """
        :param dict delta_dict
        :rtype: datetime.timedelta
    """
    days = delta_dict.get('days', 0)
    secs = delta_dict.get('secs', 0)
    ms = delta_dict.get('ms', 0)
    return datetime.timedelta(days, secs, ms)


def dict_to_time(time_dict) -> datetime.time:
    """
        :param dict time_dict
        :rtype: datetime.time
    """
    hours = time_dict.get('hours', 0)
    mins = time_dict.get('mins', 0)
    secs = time_dict.get('secs', 0)
    us = time_dict.get('us', 0)
    return datetime.time(hour=hours, minute=mins, second=secs, microsecond=us)


def hms_string_to_timedelta(hms_string) -> datetime.timedelta:
    """
        :param str hms_string:
        :rtype: datetime.timedelta
    """
    if hms_string is None:
        return None
    parts = [int(s) for s in hms_string.split(":")]
    secs = (parts[0] * (3600)) + (parts[1] * 60) + parts[2]
    return datetime.timedelta(0, secs, 0)


def hms_string_to_time(hms_string) -> datetime.time:
    """
        :param str hms_string:
        :rtype: datetime.time
    """
    # 00:00:00
    if hms_string is None:
        return None
    parts = [int(s) for s in hms_string.split(":")]
    return datetime.time(
        hour=parts[0],
        minute=parts[1],
        second=parts[2]
    )


def time_to_hms_string(time_obj) -> str:
    """
        :param dateime.time time_obj:
        :rtype: str
    """
    if time_obj is None:
        return None
    return "{:02d}:{:02d}:{:02d}".format(time_obj.hour, time_obj.minute, time_obj.second)


def timedelta_to_hms_string(delta) -> str:
    """
        :param datetime.timedelta delta:
        :rtype: str
    """
    m, s = divmod(delta.seconds, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02d" % (h, m, s)


def day_of_week_xxx(datetime) -> str:
    """
        :param datetime.datetime datetime:
        :rtype: str
    """
    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    return days[datetime.weekday()]


class ValidationError(Exception):
    """Exception class for improperly constructed objects"""

    def __init__(self, message):
        super().__init__(message)
