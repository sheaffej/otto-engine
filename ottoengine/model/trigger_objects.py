import numbers
import logging
import uuid

from ottoengine import helpers
from ottoengine.fibers import clock
from ottoengine.model import dataobjects


_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)

ATTR_PLATFORM = "platform"
ATTR_ENTITY_ID = "entity_id"


class RuleTrigger(object):

    def __init__(self, platform):
        self._platform = platform   # string

    @property
    def platform(self) -> str:
        return self._platform

    def get_dict_config(self) -> dict:
        # This will be overridden by the subclasses
        raise NotImplementedError("get_dict_config was not properly overridden")

    def serialize(self) -> dict:
        # This MAY be overridden by the subclass to accomodate special handling
        return self.get_dict_config()


class StateTrigger(RuleTrigger):
    # platform: state
    # entity_id: device_tracker.paulus, device_tracker.anne_therese

    # Optional
    # from: 'not_home'
    # to: 'home'

    def __init__(self, entity_id, to_state=None, from_state=None):
        super().__init__("state")
        # Mandatory
        self._entity_id = entity_id       # string

        # Optional
        self._to_state = to_state         # string
        self._from_state = from_state     # string

    @property
    def entity_id(self):
        return self._entity_id

    @staticmethod
    def from_dict(json):
        j = json
        kwargs = {
            ATTR_ENTITY_ID: j[ATTR_ENTITY_ID]
        }
        if "to" in j:
            kwargs["to_state"] = j["to"]
        if "from" in j:
            kwargs["from_state"] = j["from"]
        # if "for" in j:
        #     kwargs["for_delta"] = helpers.dict_to_timedelta(j["for"])
        return StateTrigger(**kwargs)

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_PLATFORM: self._platform,
            ATTR_ENTITY_ID: self._entity_id
        }
        if self._to_state:
            d["to"] = self._to_state
        if self._from_state:
            d["from"] = self._from_state
        # if self._for_delta:
        #     d["for"] = self._for_delta
        return d

    def eval_trigger(self, event_obj) -> bool:
        run = False
        _LOG.debug("got event: {}".format(event_obj.raw_msg))
        _LOG.debug("trigger defined is: {} {}".format(self, self.get_dict_config()))

        if isinstance(event_obj, dataobjects.StateChangedEvent):
            if self._entity_id in event_obj.entity_id:
                if self._to_state in {None, event_obj.new_state_obj.state}:
                    if self._from_state in {None, event_obj.old_state_obj.state}:
                        run = True

                # Check to make sure the state actually changed
                if (event_obj.old_state_obj.state == event_obj.new_state_obj.state):
                    # This can happen if the metadata about a state changed,
                    # but the main state value has not changed
                    run = False

        _LOG.debug("eval result = {}".format(run))
        return run


class NumericStateTrigger(RuleTrigger):
    # Mandatory
    # platform: numeric_state
    # entity_id: sensor.temperature

    # Optional
    # ---> Not going to support value_template yet <---
    # value_template: '{{ state.attributes.battery }}'

    # At least one of the following required
    # above: 17
    # below: 25

    def __init__(self, entity_id, above_value=None, below_value=None):
        super().__init__("numeric_state")
        # Mandatory
        # self._platform = "numeric_state"    # string
        self._entity_id = entity_id         # string

        # One of these must be specified
        self._above_value = above_value     # int or float
        self._below_value = below_value     # int or float

        if (above_value is None) and (below_value is None):
            raise helpers.ValidationError(
                "NumericStateTrigger: either above_value or below_value "
                + "must be specified ({})".format(self._entity_id)
            )

    @property
    def entity_id(self):
        return self._entity_id

    @staticmethod
    def from_dict(json):
        j = json
        entity_id = j.get(ATTR_ENTITY_ID)
        above = j.get("above_value")
        below = j.get("below_value")
        return NumericStateTrigger(entity_id, above, below)

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_PLATFORM: self._platform,
            ATTR_ENTITY_ID: self._entity_id
        }
        if self._above_value:
            d["above_value"] = self._above_value
        if self._below_value:
            d["below_value"] = self._below_value
        return d

    def eval_trigger(self, event_obj) -> bool:
        run = False

        if isinstance(event_obj, dataobjects.StateChangedEvent):
            if self._entity_id in event_obj.entity_id:
                if isinstance(event_obj.new_state_obj.state, numbers.Number):
                    if (
                        (self._above_value is None)
                        or (event_obj.new_state_obj.state > self._above_value)
                    ):
                        if (
                            (self._below_value is None)
                            or (event_obj.new_state_obj.state < self._below_value)
                        ):
                            run = True
        return run


class EventTrigger(RuleTrigger):
    # Mandatory
    # platform: event
    # event_type: MY_CUSTOM_EVENT
    # event_data:  -- I am requiring an {} for event_data if empty
    #   mood: happy
    #   key: value

    def __init__(self, event_type, event_data_obj):
        super().__init__("event")
        self._event_type = event_type     # string
        self._event_data_obj = event_data_obj

        if self._event_data_obj is None:
            self._event_data_obj = {}

    @property
    def event_type(self):
        return self._event_type

    @staticmethod
    def from_dict(json):
        j = json
        return EventTrigger(j.get("event_type"), j.get("event_data"))

    # Override
    def get_dict_config(self) -> dict:
        d = {
            ATTR_PLATFORM: self._platform,
            "event_type": self._event_type,
            "event_data": self._event_data_obj
        }
        return d

    def eval_trigger(self, event_obj: dataobjects.HassEvent) -> bool:

        if event_obj.event_type != self._event_type:
            return False

        for key in self._event_data_obj:
            if key in event_obj.data_obj:
                if event_obj.data_obj.get(key) != self._event_data_obj.get(key):
                    return False
            else:
                return False

        return True


class TimeTrigger(RuleTrigger):
    # platform: time
    # minute: '*'
    # hour: '*'
    # day_of_month: '*'
    # month: '*'
    # weekdays: '*'

    def __init__(
        self, minute=None, hour=None, day_of_month=None,
        month=None, weekdays=None, tz=None
    ):
        self._id = uuid.uuid4()
        self._timespec = clock.TimeSpec(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month=month,
            weekdays=weekdays,
            tz_name=tz
        )

    @property
    def id(self) -> str:
        return self._id

    @property
    def timespec(self) -> clock.TimeSpec:
        return self._timespec

    @staticmethod
    def from_dict(json):
        return TimeTrigger(
            json.get("minute"),
            json.get("hour"),
            json.get("day_of_month"),
            json.get("month"),
            json.get("weekdays"),
            json.get("tz")
        )

    # Override
    def get_dict_config(self) -> dict:
        o = {"platform": "time"}
        o.update(self._timespec.serialize())
        return o


class HomeAssistantTrigger(RuleTrigger):
    pass


class MqttTrigger(RuleTrigger):
    pass


class SunTrigger(RuleTrigger):
    pass


class ZoneTrigger(RuleTrigger):
    pass
