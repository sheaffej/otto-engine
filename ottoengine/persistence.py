import os
import sys
import json
import logging
import traceback

from ottoengine import config, rule_objects, trigger_objects, condition_objects, action_objects

_LOG = logging.getLogger(__name__)
_LOG.setLevel(logging.DEBUG)

BACKEND_FILE = 'file'
BACKEND_MYSQL = 'mysql'
BACKEND_SQLITE = 'sqlite'

BACKEND = BACKEND_FILE

JSON_EXTENSION = 'json'

ATTR_PLATFORM = "platform"
ATTR_CONDITION = "condition"

engine = None


def get_rules() -> list:
    """ Load the AutomationRules from JSON from the BACKEND

    Returns list of AutomationRules
    """
    rules = []

    if BACKEND == BACKEND_FILE:
        for f in os.listdir(config.JSON_RULES_DIR):
            if f.endswith(JSON_EXTENSION):
                filename = os.path.join(config.JSON_RULES_DIR, f)
                _LOG.info("Found rule file: {}".format(filename))
                rule = load_file_rule(filename)
                if rule is None:
                    _LOG.error("Rule did not load properly: {}".format(filename))
                    continue
                rules.append(rule)

    elif BACKEND == BACKEND_MYSQL:
        _error_not_implemented(BACKEND, "get_rule_ids")

    elif BACKEND == BACKEND_SQLITE:
        _error_not_implemented(BACKEND, "get_rule_ids")

    _LOG.info("Completed reading rules from peristence")
    return rules


def load_rule(rule_id) -> rule_objects.AutomationRule:
    # filename = "{}/{}{}".format(JSON_RULES_DIR, rule_id, JSON_EXTENSION)
    filename = _build_filename(rule_id)
    return load_file_rule(filename)


def load_file_rule(filename) -> rule_objects.AutomationRule:
    """ Loads JSON from a file, and returns the JSON structure"""

    if not os.path.exists(filename):
        _LOG.error("Rule file does not exist: {}".format(filename))
        return None

    _LOG.info("Opening JSON rules file: {}".format(filename))

    try:
        json_rule = json.load(open(filename))
    except Exception as e:
        _LOG.error("Error loading rule file: {}: {}".format(sys.exc_info()[0], sys.exc_info()[1]))
        return None

    result = rule_from_dict(json_rule)
    if not result.get("success"):
        _LOG.error("Error encountered parsing rule: {}".format(result.get("message")))
        return None

    return result.get("rule")


def save_rule(rule):
    _save_file_rule(rule)


def delete_rule(rule_id):
    return _delete_file_rule(rule_id)


def _log_exception(e, message):
    _LOG.error("Exception {}: {}".format(sys.exc_info()[0], sys.exc_info()[1]))
    _LOG.error("Exception Message: {}".format(message))


def _save_file_rule(rule):
    # filename = os.path.join(JSON_RULES_DIR, "{}.{}".format(rule.id, JSON_EXTENSION))
    filename = _build_filename(rule.id)
    _LOG.info("Saving rule with filename: {}".format(filename))
    with open(filename, 'w') as outfile:
        json.dump(rule.serialize(), outfile)


def _delete_file_rule(rule_id) -> bool:
    '''Returns True if file existed, False if file did not exist'''
    filename = os.path.join(config.JSON_RULES_DIR, "{}.{}".format(rule_id, JSON_EXTENSION))
    try:
        os.remove(filename)
    except FileNotFoundError:
        return False
    return True


def _build_filename(rule_id) -> str:
    return os.path.join(config.JSON_RULES_DIR, "{}.{}".format(rule_id, JSON_EXTENSION))


def _error_not_implemented(backend, operation):
    _LOG.error("{} persisted is not implemented for {}".format(backend, operation))


def rule_from_dict(rule_dict) -> dict:
    _LOG.debug("Rule JSON:  {}".format(rule_dict))

    success = True
    rule = None
    message = None

    # Create AutomationRule
    try:
        rule = rule_objects.AutomationRule(
            engine=engine,
            id=rule_dict["id"],
            description=rule_dict["description"],
            enabled=rule_dict["enabled"],
            group=rule_dict["group"],
            notes=rule_dict.get("notes", '')
        )
    except Exception as e:
        # return { "success": False, "message": ""}
        # _log_exception(e, "persistenc.rule_from_dict(): Error instantiating AutomationRule")
        success = False
        message = "Error instantiating AutomationRule: {}".format(sys.exc_info()[1])
        traceback.print_exc()
        _LOG.error(message)

    # Create Triggers
    try:
        for j in rule_dict["triggers"]:
            rule.triggers.append(_trigger_from_dict(j))
    except Exception as e:
        # _log_exception(e, "persistenc.rule_from_dict(): Error creating triggers")
        success = False
        message = "Error creating triggers: {}".format(sys.exc_info()[1])
        traceback.print_exc()
        _LOG.error(message)
        # raise e

    # Create Rule Condition
    try:
        rule.rule_condition = _condition_from_dict(rule_dict.get("rule_condition"))
    except Exception as e:
        # _log_exception(e, "persistenc.rule_from_dict(): Error creating rule condition")
        success = False
        message = "Error creating rule condition: {}".format(sys.exc_info()[1])
        traceback.print_exc()
        _LOG.error(message)

    # Create Actions
    try:
        for j in rule_dict["actions"]:
            raction = rule_objects.RuleAction()
            if "description" in j:
                raction.description = j.get("description")
            if "action_condition" in j:
                raction.action_condition = _condition_from_dict(j["action_condition"])
            for j2 in j["action_sequence"]:
                raction.action_sequence.append(_action_from_dict(j2))
            rule.actions.append(raction)
    except Exception as e:
        # _log_exception(e, "persistenc.rule_from_dict(): Error creating actions")
        success = False
        message = "Error creating actions: {}".format(sys.exc_info()[1])
        traceback.print_exc()
        _LOG.error(message)

    if success:
        return {"success": success, "rule": rule}
    else:
        return {"success": success, "message": message}


def _trigger_from_dict(trigger_json):
    trigger = None
    j = trigger_json

    if j is None:
        raise Exception("Trigger found with an empty definition (i.e. Null)")
    elif j.get(ATTR_PLATFORM) is None:
        raise Exception("Trigger defintion is missing its 'platform:' attribute")

    if "homeassistant" in j[ATTR_PLATFORM]:
        trigger = trigger_objects.HomeAssistantTrigger()
    if "state" in j[ATTR_PLATFORM]:
        trigger = trigger_objects.StateTrigger.from_dict(j)
    if "numeric_state" in j[ATTR_PLATFORM]:
        trigger = trigger_objects.NumericStateTrigger.from_dict(j)
    if "event" in j[ATTR_PLATFORM]:
        trigger = trigger_objects.EventTrigger.from_dict(j)
    if "time" in j[ATTR_PLATFORM]:
        trigger = trigger_objects.TimeTrigger.from_dict(j)
    # if "mqtt" in j[ATTR_PLATFORM]:
    #     trigger = trigger_objects.MqttTrigger()
    # if "sun" in j[ATTR_PLATFORM]:
    #     trigger = trigger_objects.SunTrigger()
    # if "zone" in j[ATTR_PLATFORM]:
    #     trigger = trigger_objects.ZoneTrigger()
    return trigger


def _condition_from_dict(condition_json):
    j = condition_json
    cond = None

    if j is None:
        # raise Exception("Condition definition is null (None)")
        return None
    elif j.get(ATTR_CONDITION) is None:
        raise Exception("Condition does not contain condition: attribute")

    # if "always" in j[ATTR_CONDITION]:
    #     cond = condition_objects.AlwaysCondition()
    if "and" in j[ATTR_CONDITION]:
        cond = condition_objects.AndCondition()
        for c in j["conditions"]:
            cond.add_condition(_condition_from_dict(c))
    elif "or" in j[ATTR_CONDITION]:
        cond = condition_objects.OrCondition()
        for c in j["conditions"]:
            cond.add_condition(_condition_from_dict(c))
    elif "numeric_state" in j[ATTR_CONDITION]:
        cond = condition_objects.NumericStateCondition.from_dict(j)
    elif "state" in j[ATTR_CONDITION]:
        cond = condition_objects.StateCondition.from_dict(j)
    elif "sun" in j[ATTR_CONDITION]:
        cond = condition_objects.SunCondition.from_dict(j)
    elif "template" in j[ATTR_CONDITION]:
        cond = condition_objects.TemplateCondition.from_dict(j)
    elif "time" in j[ATTR_CONDITION]:
        cond = condition_objects.TimeCondition.from_dict(j)
    elif "zone" in j[ATTR_CONDITION]:
        cond = condition_objects.ZoneCondition.from_dict(j)
    return cond


def _action_from_dict(action_json):
    j = action_json
    action = None
    if "service" in j:
        action = action_objects.ServiceAction.from_dict(j)
    if "condition" in j:
        action = action_objects.ConditionAction(_condition_from_dict(j))
    if "delay" in j:
        action = action_objects.DelayAction.from_dict(j)
    if "wait" in j:
        action = action_objects.WaitAction.from_dict(j)
    if "event" in j:
        action = action_objects.EventAction.from_dict(j)
    if "log_message" in j:
        action = action_objects.LogAction.from_dict(j)
    return action
