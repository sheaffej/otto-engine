import datetime
import dateutil.parser
import numbers
import logging

import pytz

from ottoengine import config, helpers


ATTR_CONDITION = "condition"
ATTR_ENTITY_ID = "entity_id"

_LOG = logging.getLogger(__name__)
_LOG.setLevel(logging.DEBUG)


class RuleCondition(object):

    def __init__(self, condition):
        # self.eval_function = None
        self._condition = condition

    def get_dict_config(self) -> dict:
        # This will be overridden by the subclasses
        raise NotImplementedError("get_dict_config() was not properly overridden")

    def serialize(self) -> dict:
        # This MAY be overridden by the subclass to accomodate special handling
        return self.get_dict_config()

    def evaluate(self, engine) -> bool:
        # This will be overridden by the subclasses
        raise NotImplementedError("evaluate() was not properly overridden")


# class AlwaysCondition(RuleCondition):
#     # condition: always

#     def __init__(self):
#         super().__init__("always")

#     def get_dict_config(self) -> dict:
#         return { "condition": "always" }

#     def evaluate(self, engine) -> bool:
#         return True;


class AndCondition(RuleCondition):
    # condition: and
    # conditions:
    #   - condition: ...
    #   - condition: ...

    def __init__(self):
        super().__init__("and")
        # self._condition = "and"
        self._conditions = []     # list of RuleConditions

    def add_condition(self, condition):
        self._conditions.append(condition)

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_CONDITION: self._condition,
            "conditions": []
        }
        for cond in self._conditions:
            d["conditions"].append(cond.get_dict_config())
        return d

    # Override
    def evaluate(self, engine) -> bool:
        _LOG.debug("Evaluating AND condtion")
        for cond in self._conditions:
            if not cond.evaluate(engine):
                _LOG.debug("Condition is FALSE: {}".format(cond.serialize()))
                return False
        return True


class OrCondition(RuleCondition):
    # condition: or
    # conditions:
    #   - condition: ...
    #   - condition: ...

    def __init__(self):
        super().__init__("or")
        # self._condition = "or"
        self._conditions = []     # list of RuleConditions

    def add_condition(self, condition):
        self._conditions.append(condition)

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_CONDITION: self._condition,
            "conditions": []
        }
        for cond in self._conditions:
            d["conditions"].append(cond.get_dict_config())
        return d

    # Override
    def evaluate(self, engine) -> bool:
        for cond in self._conditions:
            if cond.evaluate(engine):
                return True
        return False


class NumericStateCondition(RuleCondition):
    # condition: numeric_state
    # entity_id: sensor.temperature
    # above: 17
    # below: 25

    def __init__(self, entity_id, above_value=None, below_value=None):
        super().__init__("numeric_state")
        # self._condition = "numeric_state"     # string
        self._entity_id = entity_id             # string
        self._above_value = None                # numeric
        self._below_value = None                # numeric

        # Check that above_value & below_value are numbers
        if above_value is not None:
            try:
                self._above_value = float(above_value)
                if not isinstance(self._above_value, numbers.Number):
                    raise Exception()
            except Exception:
                raise helpers.ValidationError("above_value is not a number")

        if below_value is not None:
            try:
                self._below_value = float(below_value)
                if not isinstance(self._below_value, numbers.Number):
                    raise Exception()
            except Exception:
                raise helpers.ValidationError("below_value is not a number")

        if not (self._above_value or self._below_value):
            raise helpers.ValidationError(
                "NumericStateCondition: either above_value or below_value must be specified "
                + "({})".format(self._entity_id)
            )

    @staticmethod
    def from_dict(json):
        j = json
        # kwargs = {
        #     ATTR_ENTITY_ID: j[ATTR_ENTITY_ID]
        # }
        # if "above_value" in j:
        #     kwargs["above_value"] = j.get("above_value")
        # if "below_value" in j:
        #     kwargs["below_value"] = j.get("below_value")
        # return NumericStateCondition(**kwargs)
        return NumericStateCondition(
            j.get(ATTR_ENTITY_ID),
            j.get("above_value"),
            j.get("below_value")
        )

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_CONDITION: self._condition,
            ATTR_ENTITY_ID: self._entity_id
        }
        if self._above_value:
            d["above_value"] = self._above_value
        if self._below_value:
            d["below_value"] = self._below_value
        return d

    # Override
    def evaluate(self, engine) -> bool:
        _LOG.debug(
            "Evaluating NumericStateCondition: above_value: "
            + "{}, below_value: {}".format(self._above_value, self._below_value)
        )
        current_state = float(engine.states.get_entity_state(self._entity_id).state)
        _LOG.debug("Current state: {}".format(current_state))
        if isinstance(current_state, numbers.Number):
            _LOG.debug("Current state is a Number")
            if (self._above_value is None) or (current_state > self._above_value):
                _LOG.debug("above_value passed")
                if (self._below_value is None) or (current_state < self._below_value):
                    _LOG.debug("below_value passed")
                    return True
        _LOG.debug("evaluate is false")
        return False


class StateCondition(RuleCondition):
    # condition: state
    # entity_id: device_tracker.paulus
    # state: not_home

    def __init__(self, entity_id, state, for_delta=None):
        super().__init__("state")
        # self._condition = "state"
        self._entity_id = entity_id     # string
        self._state = state             # string
        # self._for_delta = for_delta     # datetime.timedelta

    @staticmethod
    def from_dict(json):
        j = json
        kwargs = {
            ATTR_ENTITY_ID: j[ATTR_ENTITY_ID],
            "state": j["state"]
        }
        # if "for" in j:
        #     kwargs["for_delta"] = helpers.dict_to_timedelta(j["for"])
        return StateCondition(**kwargs)

    # Override
    def get_dict_config(self) -> dict:
        return {
            ATTR_CONDITION: self._condition,
            ATTR_ENTITY_ID: self._entity_id,
            "state": self._state
        }
        # if self._for_delta:
        #     d["for"] = self._for_delta
        # return d

    # Override
    def evaluate(self, engine) -> bool:
        _LOG.debug(
            "Condition state: {}, current state: {}".format(
                self._state, engine.states.get_entity_state(self._entity_id).state))
        if self._state == engine.states.get_entity_state(self._entity_id).state:
            return True
        return False


class SunCondition(RuleCondition):
    # condition: sun
    # after: sunset               # sunset or sunrise
    # after_offset: "-1:00:00"    # Optional offset value
    # ...or...
    # before: sunset              # sunset or sunruse
    # before_offset: "-1:00:00"    # Optional offset value

    def __init__(self, after=None, before=None, after_offset=None, before_offset=None):
        super().__init__("sun")
        # self._condition = "sun"
        self._entity_id = "sun.sun"
        # Need one of these
        self._after = after         # string: sunrise or sunset
        self._before = before       # string: sunrise or sunset
        # Optional, must match before or after above
        self._after_offset = after_offset       # datetime.timedelta
        self._before_offset = before_offset     # datetime.timedelta

        if not (self._after or self._before):
            raise helpers.ValidationError(
                "SunCondition: either before or after must be specified")
        elif (self._after and self._before):
            raise helpers.ValidationError(
                "SunCondition: before and after cannot both be specified")

    # Override
    def evaluate(self, engine) -> bool:
        now = datetime.datetime.now()   # datetime.datetime

        if self._before_offset is None:
            self._before_offset = datetime.timedelta(0)     # datetime.timedelta
        if self._after_offset is None:
            self._after_offset = datetime.timedelta(0)      # datetime.timedelta

        sun_state = engine.states.get_entity_state(self._entity_id)
        next_rising = dateutil.parser.parse(
            sun_state.attributes.get('next_rising'))    # datetime.datetime
        next_setting = dateutil.parser.parse(
            sun_state.attributes.get('next_setting'))   # datetime.datetime

        # False if now is already after the specified time before sunrise
        if self._before == 'sunrise' and now > (next_rising + self._before_offset):
            return False

        # False if now is already after the specified time before sunset
        elif self._before == 'sunset' and now > (next_setting + self._before_offset):
            return False

        # False if now is still before the specified time after sunrise
        if self._after == 'sunrise' and now < (next_rising + self._after_offset):
            return False

        # False if now is still before the specified timea fter sunset
        elif self._after == 'sunset' and now < (next_setting + self._after_offset):
            return False

        return True

    @staticmethod
    def from_dict(json):
        j = json
        kwargs = {}
        if "after" in j:
            kwargs["after"] = j["after"]
        if "before" in j:
            kwargs["before"] = j["before"]
        if "after_offset" in j:
            kwargs["after_offset"] = j["after_offset"]
        if "before_offset" in j:
            kwargs["before_offset"] = j["before_offset"]
        return SunCondition(**kwargs)

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_CONDITION: self._condition
        }
        if self._after:
            d["after"] = self._after
        if self._before:
            d["before"] = self._before
        if self._after_offset:
            d["after_offset"] = self._after_offset
        if self._before_offset:
            d["before_offset"] = self._before_offset
        return d


class TemplateCondition(RuleCondition):
    # condition: template
    # value_template: '{{ states.device_tracker.iphone.attributes.battery > 50 }}'

    def __init__(self, value_template):
        super().__init__("template")
        # self._condition = "template"
        self._value_template = value_template   # template string

    @staticmethod
    def from_dict(json):
        return TemplateCondition(json["value_template"])

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_CONDITION: self._condition,
            "value_template": self._value_template
        }
        return d


class TimeCondition(RuleCondition):
    # condition: time
    #    At least one of the following is required.
    # after: '15:00:00'
    # before: '02:00:00'
    # weekday:
    #   - mon
    #   - wed
    #   - fri

    def __init__(self, after=None, before=None, weekday=None, tz_name=None):
        super().__init__("time")
        # self._condition = "time"
        self._after = after         # datetime.time
        self._before = before       # datetime.time
        self._weekday = weekday     # list of strings: [mon, tue, wed, thu, fri, sat, sun]
        self._tz_name = tz_name     # Default to config.TZ if not specified

        if self._tz_name is None:
            self._tz_name = config.TZ

        if not (self._after or self._before or self._weekday):
            raise helpers.ValidationError(
                "TimeCondition: must specify one of: after, before, or weekday")

    @staticmethod
    def from_dict(json):
        j = json
        # kwargs = {}
        # if "after" in j:
        #     kwargs["after"] = helpers.dict_to_time(j.get("after"))
        # if "before" in j:
        #     kwargs["before"] = helpers.dict_to_time(j.get("before"))
        # if "weekday" in j:
        #     kwargs["weekday"] = j.get("weekday")
        tz_name = j.get("tz")
        if tz_name is None:
            tz_name = config.TZ

        return TimeCondition(
            helpers.hms_string_to_time(j.get("after"), tz_name),
            helpers.hms_string_to_time(j.get("before"), tz_name),
            helpers.hms_string_to_time(j.get("weekday"), tz_name)
        )

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_CONDITION: self._condition
        }
        if self._after:
            # d["after"] = helpers.time_to_dict(self._after)
            d["after"] = helpers.time_to_hms_string(self._after)
        if self._before:
            # d["before"] = helpers.time_to_dict(self._before)
            d["before"] = helpers.time_to_hms_string(self._before)
        if self._weekday:
            d["weekday"] = self._weekday
        return d

    # Override
    def evaluate(self, engine) -> bool:
        """Test if current time is within the period listed in the condition.

        This condition test essentially determines if the current time is within
        a "period" bounded by _after and _before.

        Where, C is the current time:

            _after  --> C --> _before  = returns True
            _before --> C --> _after   = returns False

        If _after or _before are not defined, then they are set to the beginning and end of day,
        respectively:
            _after  = 00:00:00
            _before = 23:59:59

        If the "period" crosses midnight, then we can consider the period being broken in
        to 2 smaller periods:

            [00:00:00 --> _before] and [_after --> 23:59:59]

        ...and therefore if C is in the middle (between _before and _after) then it is NOT
        in the period
        So if _before is earlier than _after, we can test for the inverse:

            C is NOT between _before and _after = True (within the period)
        """
        now = datetime.datetime.now(tz=pytz.timezone(config.TZ))
        now_time = now.time()

        # Snap _after and _before to day's edges if not specified
        if self._after is None:
            self._after = datetime.time(0)
        if self._before is None:
            self._before = datetime.time(23, 59, 59, 999999)

        if self._after < self._before:     # Test for a period within a day
            if not self._after <= now_time < self._before:  # C is NOT in the mid-day period
                return False
        else:
            # Period crosses midnight
            if self._before <= now_time < self._after:
                # C is in the mid-day non-period (i.e. not in the period)
                return False

        if self._weekday is not None:
            now_weekday = helpers.day_of_week_xxx(now)
            if now_weekday not in self._weekday:
                return False

        return True


class ZoneCondition(RuleCondition):
    # condition: zone
    # entity_id: device_tracker.paulus
    # zone: zone.home

    def __init__(self, entity_id, zone):
        super().__init__("zone")
        # self._condition = "zone"
        self._entity_id = entity_id     # string
        self._zone = zone               # string

    @staticmethod
    def from_dict(json):
        j = json
        kwargs = {
            ATTR_ENTITY_ID: j[ATTR_ENTITY_ID],
            "zone": j["zone"]
        }
        return ZoneCondition(**kwargs)

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_CONDITION: self._condition,
            ATTR_ENTITY_ID: self._entity_id,
            "zone": self._zone
        }
        return d

    # Override
    def evaluate(self, states) -> bool:
        if self._zone == states.get_entity_state(self._entity_id):
            return True
        return False
