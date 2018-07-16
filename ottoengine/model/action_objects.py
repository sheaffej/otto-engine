import asyncio
import logging

from ottoengine import const, helpers
from ottoengine.model import dataobjects

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)


class RuleActionItem(object):
    """ This is a single action step in an action sequence """

    def get_dict_config(self) -> dict:
        # This will be overridden by the subclasses
        raise NotImplementedError("get_dict_config was not properly overridden")

    def serialize(self) -> dict:
        # This MAY be overridden by the subclass to accomodate special handling
        return self.get_dict_config()

    async def async_execute(self, engine) -> bool:
        '''Runs the action.
            Returns True if action was successful.
            Returns False if the action was unsuccessful.
        '''
        # This will be overridden by the subclasses
        raise NotImplementedError("async_execute was not properly overridden")


class ServiceAction(RuleActionItem):
    # domain: light
    # service: turn_on
    # data:
    #   entity_id: group.bedroom
    #   brightness: 100

    def __init__(self, domain, service, entity_id=None, data_dict={}):
        self._domain = domain
        self._service = service         # string
        self._data_dict = data_dict     # {} dictionary

        if entity_id is not None:
            self._data_dict["entity_id"] = entity_id

    # Override
    async def async_execute(self, engine):
        _LOG.info("Service called - domain: {}, service: {}, data: {}".format(
            self._domain, self._service, self._data_dict)
        )
        await engine.call_service(
            dataobjects.ServiceCall(self._domain, self._service, self._data_dict)
        )
        return True

    @staticmethod
    def from_dict(dict_obj):
        # j = json
        # kwargs = {
        #     "domain": j['domain'],
        #     "service": j["service"]
        # }
        # if "data" in j:
        #     kwargs["data"] = j["data"]
        # return ServiceAction(**kwargs)

        domain = dict_obj.get(const.DOMAIN)
        service = dict_obj.get(const.SERVICE)
        data = dict_obj.get(const.DATA, [])
        return ServiceAction(domain, service, data_dict=data)

    # Override
    def get_dict_config(self) -> dict:
        d = {
            "domain": self._domain,
            "service": self._service,
        }
        if self._data_dict:
            d["data"] = self._data_dict
        return d


class ConditionAction(RuleActionItem):
    # This is just a condition object

    def __init__(self, condition_obj):
        self._condition_obj = condition_obj

    # No from_dict function since this is just a condition object
    # We use the _condition_from_dict() function in persistence.py instead

    # Override
    async def async_execute(self, engine):
        '''Tests the condition.  Returns the result of the test'''
        result = False
        if self._condition_obj.evaluate(engine):
            result = True

        _LOG.info("Condition action is {}: {}".format(result, self._condition_obj.serialize()))
        return result

    # Override
    def get_dict_config(self) -> dict:
        return self._condition_obj.get_condition_config()


class DelayAction(RuleActionItem):
    # delay: 00:01:30

    def __init__(self, delay_delta):
        self._delay_delta = delay_delta     # datetime.timedelta

    # Override
    async def async_execute(self, engine):
        delay_secs = self._delay_delta.total_seconds()
        _LOG.info("Delay action for {} seconds".format(delay_secs))
        await asyncio.sleep(delay_secs)
        return True

    @staticmethod
    def from_dict(json):
        return DelayAction(helpers.hms_string_to_timedelta(json["delay"]))

    # Override
    def get_dict_config(self) -> dict:
        # To re-create: timedelta(days, seconds, microseconds)
        return {
            "delay": helpers.timedelta_to_hms_string(self._delay_delta)
        }


class LogAction(RuleActionItem):
    # log_message: message

    def __init__(self, message):
        self._message = message

    @staticmethod
    def from_dict(json):
        return LogAction(json.get("log_message"))

    # Overrides
    async def async_execute(self, engine):
        _LOG.info("LogAction: {}".format(self._message))
        return True

    def get_dict_config(self) -> dict:
        return {"log_message": self._message}
