import os
import sys
import json
import logging
import traceback

from ottoengine.model import rule_objects, trigger_objects, condition_objects, action_objects

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)

BACKEND_FILE = 'file'
BACKEND_MYSQL = 'mysql'
BACKEND_SQLITE = 'sqlite'

JSON_EXTENSION = 'json'

ATTR_PLATFORM = "platform"
ATTR_CONDITION = "condition"


def _log_exception(e, message):
    _LOG.error("Exception {}: {}".format(sys.exc_info()[0], sys.exc_info()[1]))
    _LOG.error("Exception Message: {}".format(message))


def _error_not_implemented(backend, operation):
    _LOG.error("{} persisted is not implemented for {}".format(backend, operation))


class PersistenceManager:

    def __init__(self, engine_obj, json_rules_dir):
        """
            :param engine.OttoEngine engine_obj:
            :param str json_rules_dir:
        """
        self._engine = engine_obj
        self._json_rules_dir = json_rules_dir

    # ~~~~~~~~~~~~~~
    # Public methods
    # ~~~~~~~~~~~~~~

    def get_rules(self, json_rules_dir: str, backend: str='file') -> list:
        """ Load the AutomationRules from JSON from the BACKEND
        Returns list of AutomationRules
        :rtype: list(rule_objects.AutomationRule)
        """
        rules = []

        if backend == BACKEND_FILE:
            for file in os.listdir(json_rules_dir):
                if file.endswith(JSON_EXTENSION):
                    filename = os.path.join(json_rules_dir, file)
                    _LOG.info("Found rule file: {}".format(filename))
                    rule = self._load_file_rule(filename)
                    if rule is None:
                        _LOG.error("Rule did not load properly: {}".format(filename))
                        continue
                    rules.append(rule)

        elif backend == BACKEND_MYSQL:
            _error_not_implemented(backend, "get_rule_ids")

        elif backend == BACKEND_SQLITE:
            _error_not_implemented(backend, "get_rule_ids")

        _LOG.info("Completed reading rules from peristence")
        return rules

    def load_rule(self, rule_id: str) -> rule_objects.AutomationRule:
        filename = self._build_filename(rule_id)
        return self._load_file_rule(filename)

    def save_rule(self, rule: rule_objects.AutomationRule):
        self._save_file_rule(rule)

    def delete_rule(self, rule_id: str) -> bool:
        return self._delete_file_rule(rule_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~
    # Non-public helper methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~

    def _load_file_rule(self, filename: str) -> rule_objects.AutomationRule:
        """ Loads JSON from a file, and returns the JSON structure"""

        if not os.path.exists(filename):
            _LOG.error("Rule file does not exist: {}".format(filename))
            return None

        _LOG.info("Opening JSON rules file: {}".format(filename))

        try:
            json_rule = json.load(open(filename))
        except Exception as e:
            _LOG.error(
                "Error loading rule file: {}: {}".format(sys.exc_info()[0], sys.exc_info()[1]))
            return None

        result = self.rule_from_dict(json_rule)
        if not result.get("success"):
            _LOG.error("Error encountered parsing rule: {}".format(result.get("message")))
            return None

        return result.get("rule")

    def _save_file_rule(self, rule: rule_objects.AutomationRule):
        filename = self._build_filename(rule.id)
        _LOG.info("Saving rule with filename: {}".format(filename))
        with open(filename, 'w') as outfile:
            json.dump(rule.serialize(), outfile)

    def _delete_file_rule(self, rule_id: str) -> bool:
        '''Returns True if file existed, False if file did not exist'''
        # filename = os.path.join(config.JSON_RULES_DIR, "{}.{}".format(rule_id, JSON_EXTENSION))
        filename = self._build_filename(rule_id)
        try:
            os.remove(filename)
        except FileNotFoundError:
            return False
        return True

    def _build_filename(self, rule_id: str) -> str:
        return os.path.join(self._json_rules_dir, "{}.{}".format(rule_id, JSON_EXTENSION))

    # ~~~~~~~~~~~~~~~~~~~~
    # Rule loading methods
    # ~~~~~~~~~~~~~~~~~~~~

    def rule_from_dict(self, rule_dict: dict) -> dict:
        _LOG.debug("Rule JSON:  {}".format(rule_dict))

        success = True
        rule = None
        message = None

        # Create AutomationRule
        try:
            rule = rule_objects.AutomationRule(
                engine=self._engine,
                id=rule_dict.get("id"),
                description=rule_dict.get("description", ''),
                enabled=rule_dict.get("enabled", True),
                group=rule_dict.get("group", ''),
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
                rule.triggers.append(self._trigger_from_dict(j))
        except Exception as e:
            # _log_exception(e, "persistenc.rule_from_dict(): Error creating triggers")
            success = False
            message = "Error creating triggers: {}".format(sys.exc_info()[1])
            traceback.print_exc()
            _LOG.error(message)
            # raise e

        # Create Rule Condition
        try:
            rule.rule_condition = self._condition_from_dict(rule_dict.get("rule_condition"))
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
                    raction.action_condition = self._condition_from_dict(j["action_condition"])
                for j2 in j["action_sequence"]:
                    raction.action_sequence.append(self._action_from_dict(j2))
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

    def _trigger_from_dict(self, trigger_json: dict) -> trigger_objects.RuleTrigger:
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

    def _condition_from_dict(self, condition_json: dict) -> condition_objects.RuleCondition:
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
                cond.add_condition(self._condition_from_dict(c))
        elif "or" in j[ATTR_CONDITION]:
            cond = condition_objects.OrCondition()
            for c in j["conditions"]:
                cond.add_condition(self._condition_from_dict(c))
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

    def _action_from_dict(self, action_json: dict) -> action_objects.RuleActionItem:
        j = action_json
        action = None
        if "service" in j:
            action = action_objects.ServiceAction.from_dict(j)
        if "condition" in j:
            action = action_objects.ConditionAction(self._condition_from_dict(j))
        if "delay" in j:
            action = action_objects.DelayAction.from_dict(j)
        if "wait" in j:
            action = action_objects.WaitAction.from_dict(j)
        if "event" in j:
            action = action_objects.EventAction.from_dict(j)
        if "log_message" in j:
            action = action_objects.LogAction.from_dict(j)
        return action
