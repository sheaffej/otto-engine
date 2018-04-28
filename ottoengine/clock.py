import asyncio
import datetime
import pytz
import croniter
import logging

from ottoengine import config, fibers

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)


TICK_INTERVAL_SECONDS = 1  # Number of seconds between ticks

TICK_GRACE_SECONDS = 60     # Number of seconds past a scheduled event that it can still be executed
                            # If the event isn't executed by this time after it's scheduled time
                            # don't execute it, but just reschedule it for it's next time


def utcnow():
    return datetime.datetime.now(pytz.utc)


class TimeSpec(object):

    def __init__(self, minute=None, hour=None, day_of_month=None, month=None, weekdays=None, tz_name=None):

        # This object follows cron syntax:  https://en.wikipedia.org/wiki/Cron
        self._minute = minute
        self._hour = hour
        self._day_of_month = day_of_month
        self._month = month
        self._weekdays = weekdays      # 0-6 is Sun to Sat; or 1-7 is Mon to Sun
        self._tz_name = tz_name
        if tz_name is None:
            self._tz_name = config.TZ
        

    def _create_cron_spec(self):
        minute = self._minute
        hour = self._hour
        day_of_month = self._day_of_month
        month = self._month
        weekdays = self._weekdays


        if minute is None:
            minute = '*'
        if hour is None:
            hour = '*'
        if day_of_month is None:
            day_of_month = '*'
        if month is None:
            month = '*'
        if weekdays is None:
            weekdays = '*'

        return "{} {} {} {} {}".format(minute, hour, day_of_month, month, weekdays)


    #### Public Methods ####

    def next_time_from_now(self) -> datetime.datetime:
        return self.next_time_from(utcnow())


    def next_time_from(self, dt) -> datetime.datetime:

        # Convert dt so it's the same TZ as the TimeSpec
        # if self._is_utc:
        #     dt = dt.astimezone(pytz.utc)
        #     # print("converting dt to UTC: {}".format(dt))
        # else:
        #     dt = dt.astimezone(pytz.timezone(config.TZ))
        #     # print("convering dt to LOCALTZ: {}".format(dt))

        cron = croniter.croniter(self._create_cron_spec(), dt.astimezone(pytz.timezone(self._tz_name)))
        return cron.get_next(datetime.datetime)

        return dt



    def serialize(self) -> dict:
        o = {}

        if self._minute is not None:
            o["minute"] = self._minute

        if self._hour is not None:
            o["hour"] = self._hour

        if self._day_of_month is not None:
            o["day_of_month"] = self._day_of_month

        if self._weekdays is not None:
            o["weekdays"] = self._weekdays

        if self._month is not None:
            o["month"] = self._month

        if self._tz_name is not None:
            o["tz"] = self._tz_name

        return o


    #### Static Methods ####

    @staticmethod
    def from_dict(dict_obj):
        o = dict_obj
        return TimeSpec(
            minute = o.get("minute"),
            hour = o.get("hour"),
            day_of_month = o.get("day_of_month"),
            month = o.get("month"),
            weekdays = o.get("weekdays"),
            tz_name = o.get("tz", config.TZ)
        )

# class TimeSpec



class ClockAlarm(object):
    '''
    This is what sits on the ClockTriggers queue.
    A ClockAlarm can hold multiple actions to trigger at its clock time
    '''
    def __init__(self, alarm_time):
        self.alarm_time = alarm_time    # This is a datetime object
        self.actions = []               # List of AlarmActions


    def add_action(self, action):
        self.actions.append(action)


    def remove_action(self, trigger_guid):
        for pos, action in self.actions:
            # TimeSpec Action
            if isinstance(action, AlarmTimeSpecAction):
                if action.id == trigger_guid:
                    del self.actions[pos]
# class ClockAlarm


class AlarmAction(object):
    def __init__(self, action_function):
        self.action_function = action_function
# class AlarmItem


class AlarmTimeSpecAction(AlarmAction):
    def __init__(self, id: str, action_function, timespec: TimeSpec):
        super().__init__(action_function)
        self.id = id
        self.timespec = timespec
# clas AlarmTimeSpecTime




class EngineClock (fibers.Fiber):

    def __init__(self, loop=None):
        super().__init__()
        self._loop = loop
        self._timeline = []     # list of ClockAlarms; one for each time at which to do something

        if self._loop is None:
            self._loop = asyncio.get_event_loop()


    #### Public methods ####

    def add_timespec_action(self, id: str, action_function, timespec: TimeSpec):
        action = AlarmTimeSpecAction(id, action_function, timespec)
        self._add_action_to_timeline(timespec.next_time_from_now(), action)

    def remove_timespec_action(self, id: str):
        for alarm in self._timeline:
            for pos, action in enumerate(alarm.actions):
                if action.id == id:
                    print("found timespec action: {}".format(id))
                    alarm.actions.remove(action)


    #### Private methods ####

    # Override of Fiber base class.  Called by async Fiber.async_run()
    async def _async_run(self):
        
        # Start the _tick() loop
        while self._running:
            await self._tick()                          # Execute tick
            await asyncio.sleep(TICK_INTERVAL_SECONDS)  # Sleep until next tick


    async def _tick(self):

        # If no timeline, do nothing
        if len(self._timeline) == 0:
            return

        # If now() is >= 1st element of timeline
        while utcnow() >= self._timeline[0].alarm_time:

            # pop it off the timeline
            alarm = self._timeline.pop(0)

            # If alarm is too old: > TICK_GRACE_SECONDS before now()
            if utcnow() > alarm.alarm_time + datetime.timedelta(seconds=TICK_GRACE_SECONDS):
                _LOG.warn("Clock _tick found alarms too old (> TICK_GRACE_SECONDS: {} old)".format(TICK_GRACE_SECONDS))
                _LOG.warn(self._format_timeline())


            # Process its actions
            for action in alarm.actions:
                self._loop.create_task(action.action_function())

                # Schedule the action's next time
                if isinstance(action, AlarmTimeSpecAction):
                    self.add_timespec_action(action.id, action.action_function, action.timespec)

        _LOG.debug("Clock _tick(): next alarm is {} seconds away".format((self._timeline[0].alarm_time - utcnow()).seconds))


    def _add_action_to_timeline(self, alarm_time: datetime.datetime, action: AlarmAction):
        # Handle empty timeline case
        if len(self._timeline) == 0:
            _LOG.debug("Clock has empty timeline.  Adding first alarm at: {}".format(alarm_time))
            alarm = ClockAlarm(alarm_time)
            alarm.add_action(action)
            self._timeline.append(alarm)
            return

        for pos, alarm in enumerate(self._timeline):

            _LOG.debug("new.alarm_time: {} | alarm.alarm_time: {}".format(alarm_time, alarm.alarm_time))
            
            # if new.alarm_time == [pos].alarm_time --> add action to existing alarm
            if alarm_time == alarm.alarm_time:
                _LOG.debug("Found match of existing alarm, adding to its list of actions. Length: {}".format(len(alarm.actions)+1))
                alarm.add_action(action)
                break

            # if new.alarm_time < [pos].alarm_time --> insert new alarm at [pos]
            elif alarm_time < alarm.alarm_time:
                _LOG.debug("Adding new alarm at postion {} in the timeline. Alarm: {}".format(pos, alarm_time))
                alarm = ClockAlarm(alarm_time)
                alarm.add_action(action)
                self._timeline.insert(pos, alarm)
                break

            # if we are at the end of the timeline --> append a new alarm at the end
            elif len(self._timeline) == pos+1 :
                _LOG.debug("Adding new alarm at the end of the timeline. Alarm: {}".format(alarm_time))
                alarm = ClockAlarm(alarm_time)
                alarm.add_action(action)
                self._timeline.append(alarm)
                break

            # else --> pos++ and loop again

        _LOG.debug(self._format_timeline())



    def _format_timeline(self) -> str:
        p = "Printing clock alarm timeline..."
        for alarm in self._timeline:
            p += "\nAlarm: {}".format(alarm.alarm_time.astimezone(pytz.timezone(config.TZ)))
            for i, action in enumerate(alarm.actions):
                if isinstance(action, AlarmTimeSpecAction):
                    p += "\n   Action {}: {}".format(i, action.id)
                else:
                    p += "\n   Action: {}".format(action)
        return p

# class EngineClock


