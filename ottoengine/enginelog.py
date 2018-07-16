from ottoengine import helpers

SERVICE_CALL = "service_call"
TRIGGER_FIRED = "trigger_fired"
CONDITION_TESTED = "condition_tested"
CONDITION_PASSED = "condition_passed"
RULE_COMPLETED = "rule_completed"
DEBUG = "debug"


class EngineLog:
    def __init__(self, max_logs=100):
        self._log = []
        self._max_logs = max_logs

    def add(self, logtype: str, logentry: dict):
        if self._max_logs > 0:
            self._log.append({
                "ts": str(helpers.nowutc()),
                "type": logtype,
                "entry": logentry,
            })
            self._trim_log()

    def get_logs(self):
        return self._log.copy()

    def set_max_logs(self, max_logs):
        self._max_logs = max_logs
        self._trim_log()

    def _trim_log(self):
        while len(self._log) > self._max_logs:
            del self._log[0]
