import logging

from ottoengine.fibers import clock
from ottoengine.model import action_objects, trigger_objects


_LOG = logging.getLogger(__name__)
_LOG.setLevel(logging.DEBUG)


class AutomationRule(object):

    def __init__(self, engine, id, description='', enabled=True, group=None, notes=''):
        self._engine = engine
        self.id = id
        self.description = description
        self.enabled = enabled
        self.group = group
        self.triggers = []          # list of RuleTrigger
        self.rule_condition = None  # a RuleCondition
        self.actions = []           # list of RuleAction
        self.notes = notes          # Notes should never be null; empty string at least

    def serialize(self) -> dict:
        j = {}
        j["id"] = self.id
        j["description"] = self.description
        j["enabled"] = self.enabled
        j["group"] = self.group
        j["notes"] = self.notes
        j["triggers"] = []
        for t in self.triggers:
            j["triggers"].append(t.serialize())
        if self.rule_condition is not None:
            j["rule_condition"] = self.rule_condition.serialize()
        j["actions"] = []
        for a in self.actions:
            j["actions"].append(a.serialize())
        return j

    def get_state_listeners(self) -> list:
        '''Returns a list of EventListener objects to be registered as event listeners.'''
        listeners = []
        for trigger in self.triggers:

            # Only if the trigger is Event-related
            if isinstance(trigger, (
                trigger_objects.StateTrigger,
                trigger_objects.NumericStateTrigger
                # trigger_objects.EventTrigger
            )):

                async def async_handle_trigger(event_obj, trigger=trigger):
                    # The trigger arg forces early binding of trigger
                    # http://stackoverflow.com/a/3431699/3784722
                    '''Called when an event occurs.  Is passed in the object representing the event
                    that has occurred.  Determines if the event matches the trigger.  If so,
                    schedules the rule's condition to be evaluated on the event loop.event
                    '''
                    if self.enabled:
                        if trigger.eval_trigger(event_obj):
                            _LOG.info(
                                "Rule Trigger passed.  Scheduling rule condition evaluation "
                                + "for rule {}".format(self.id))
                            self._engine.schedule_task(self.async_eval_rule())

                listeners.append(StateListener(self.id, trigger.entity_id, async_handle_trigger))
        return listeners

    def get_event_listeners(self) -> list:
        listeners = []
        for trigger in self.triggers:
            if isinstance(trigger, trigger_objects.EventTrigger):

                async def async_handle_trigger(event_obj, trigger=trigger):
                    # The trigger arg forces early binding of trigger
                    # http://stackoverflow.com/a/3431699/3784722
                    ''' Called when an event occurs.  Is passed in the object representing the event
                    that has occurred.  Determines if the event matches the trigger.  If so,
                    schedules the rule's condition to be evaluated on the event loop.event
                    '''
                    if self.enabled:
                        if trigger.eval_trigger(event_obj):
                            _LOG.info(
                                "Rule Trigger passed.  Scheduling rule condition evaluation "
                                + "for rule {}".format(self.id))
                            self._engine.schedule_task(self.async_eval_rule())

                listeners.append(EventListener(self.id, trigger.event_type, async_handle_trigger))
        return listeners

    def get_time_listeners(self) -> list:
        time_triggers = []
        for trigger in self.triggers:

            # Only if the trigger is a TimeTrigger
            if isinstance(trigger, trigger_objects.TimeTrigger):

                async def async_handle_time_trigger():
                    if self.enabled:
                        _LOG.info(
                            "Rule Time Trigger firing.  Scheduling rule condition evaluation "
                            + "for rule {}".format(self.id))
                        self._engine.schedule_task(self.async_eval_rule())

                time_triggers.append(
                    TimeListener(
                        self.id, trigger.id, trigger.timespec, async_handle_time_trigger
                    )
                )

        return time_triggers

    async def async_eval_rule(self):
        ''' Called after a triggered RuleTrigger evals to True.
        This function will evalutes the AutomationRule's rule_condition.
        If the rule should run, then this function will schedule the rule's
        actions to run.
        '''
        _LOG.info("Evaluating rule condition for rule: {}".format(self.id))
        if self.rule_condition is None or self.rule_condition.evaluate(self._engine):
            _LOG.debug("Rule condition passed. Scheduling actions for rule: {}".format(self.id))
            self._engine.schedule_task(self.async_run_actions())

    async def async_run_actions(self):
        '''Run the action sequences'''
        _LOG.info("AutomationRule {} is running".format(self.id))

        for seqId, action_seq in enumerate(self.actions):
            await action_seq.async_run(self._engine, self.id, seqId)


class RuleAction(object):
    """ This is the set of action sequences, and their conditions that
    and Ottomation will run if the RuleCondition is True
    """

    # {
    #   "action_condition": { RulCondition },
    #   "action_sequence": [ RuleActionItem, RuleActionItem, ... ]
    # }

    def __init__(self):
        self.description = None
        self.action_condition = None
        self.action_sequence = []

    def get_sequence_dict_config(self):
        seq = []
        for action in self.action_sequence:
            seq.append(action.get_dict_config())
        return seq

    def serialize(self) -> dict:
        j = {}
        j["description"] = self.description
        if self.action_condition is not None:
            j["action_condition"] = self.action_condition.serialize()
        seq = []
        for action in self.action_sequence:
            seq.append(action.serialize())
        j["action_sequence"] = seq
        return j

    async def async_run(self, engine, ruleId, seqId):
        _LOG.debug("Evaluating action sequence rule (rule: {}, seq#: {})".format(ruleId, seqId))
        if (self.action_condition is None) or (self.action_condition.evaluate(engine)):
            _LOG.debug("Rule {} action sequence #{} will run".format(ruleId, seqId))
            for actId, action in enumerate(self.action_sequence):
                success = await action.async_execute(engine)
                if not success:
                    if isinstance(action, action_objects.ConditionAction):
                        _LOG.info(
                            ("Rule {} aborting action sequence #{} due to false "
                             + "Condition at action #{}").format(ruleId, seqId, actId))
                    else:
                        _LOG.warn(
                            ("Rule {} aborting action sequence #{} due to action "
                             + "failure at action #{}").format(ruleId, seqId, actId))
                    return
        else:
            _LOG.debug("Rule action will not run: {}".format(self.action_condition.serialize()))


class HassListener(object):
    def __init__(self, rule_id, trigger_function):
        self._rule_id = rule_id
        self._trigger_function = trigger_function

    @property
    def rule_id(self):
        return self._rule_id

    @property
    def trigger_function(self):
        return self._trigger_function


class StateListener(HassListener):
    def __init__(self, rule_id, entity_id, trigger_function):
        super().__init__(rule_id, trigger_function)
        self._entity_id = entity_id

    @property
    def entity_id(self):
        return self._entity_id


class EventListener(HassListener):
    def __init__(self, rule_id, event_type, trigger_function):
        super().__init__(rule_id, trigger_function)
        self._event_type = event_type
        # self._event_data = event_data

    @property
    def event_type(self):
        return self._event_type


class TimeListener(HassListener):
    def __init__(self, rule_id, listener_id: str, timespec: clock.TimeSpec, trigger_function):
        """
            :param str rule_id:
            :param str listener_id:
            :param clock.TimeSpec timespec:
            :param function trigger_function:
        """
        super().__init__(rule_id, trigger_function)
        self._listener_id = listener_id
        self._timespec = timespec

    @property
    def listener_id(self):
        return self._listener_id

    @property
    def timepsec(self):
        return self._timespec
