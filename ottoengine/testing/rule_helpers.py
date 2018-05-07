
class AutomationRuleSpec:

    def __init__(self, id, group, description='', enabled=True, notes=''):
        self.id = id
        self.group = group
        self.triggers = []          # list of RuleTrigger
        self.rule_condition = None  # a RuleCondition
        self.actions = []           # list of RuleAction
        self.notes = notes          # Notes should never be null; empty string at least
        self.description = description
        self.enabled = enabled

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

    def add_trigger(self, trigger):
        self.triggers.append(trigger)

    def add_rule_condition(self, condition):
        self.rule_condition = condition

    def add_action(self, action):
        self.actions.append(action)
