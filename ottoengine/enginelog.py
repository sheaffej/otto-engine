from ottoengine import helpers

SERVICE_CALL = "service_call"
TRIGGER_FIRED = "trigger_fired"
CONDITION_TESTED = "condition_tested"
CONDITION_PASSED = "condition_passed"
RULE_COMPLETED = "rule_completed"
DEBUG = "debug"


class EngineLog:
    def __init__(self, max_entries=100):
        self._log = []
        self._max_entries = max_entries

    def add(self, logtype: str, logentry: dict):
        self._log.append({
            "ts": str(helpers.nowutc()),
            "type": logtype,
            "entry": logentry,
        })

    def get_logs(self):
        return self._log.copy()

    def set_max_entries(self, max_entries):
        self._max_entries = max_entries
