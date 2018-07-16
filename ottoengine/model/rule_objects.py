# import asyncio
import logging

from ottoengine.model import action_objects, trigger_objects

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)


class AutomationRule(object):

    def __init__(self, id, description='', enabled=True, group=None, notes=''):
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


class HassListener(object):
    def __init__(self, rule: AutomationRule, trigger: trigger_objects.ListenerTrigger):
        self._rule = rule
        self._trigger = trigger

    @property
    def rule(self):
        return self._rule

    @property
    def trigger(self):
        return self._trigger


def get_listeners(rule: AutomationRule) -> list:
    '''Returns a list of HassListener objects to be registered as event listeners.'''
    listeners = []
    for trigger in rule.triggers:
            listeners.append(HassListener(rule, trigger))
    return listeners


async def async_run_action_seq(rule: AutomationRule, seqId: int, engine):
    action_seq = rule.actions[seqId]
    _LOG.debug("Evaluating rule {} action seq# {}".format(rule.id, seqId))
    if (action_seq.action_condition is None) or (action_seq.action_condition.evaluate(engine)):
        _LOG.debug("Rule {} action seq# {} will run".format(rule.id, seqId))
        for actId, action in enumerate(action_seq.action_sequence):

            success = await action.async_execute(engine)
            if not success:
                if isinstance(action, action_objects.ConditionAction):
                    _LOG.info(
                        ("Rule {} aborting action seq# {} due to false "
                            + "condition at action# {}").format(rule.id, seqId, actId))
                else:
                    _LOG.warn(
                        ("Rule {} aborting action seq# {} due to action "
                            + "failure at action# {}").format(rule.id, seqId, actId))
                return
    else:
        _LOG.debug("Rule {} action seq# {} will not run: {}".format(
            rule.id, seqId, action.action_condition.serialize()))
