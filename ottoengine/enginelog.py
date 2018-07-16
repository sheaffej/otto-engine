from ottoengine import helpers

EVENT = "event"
ERROR = "error"
SERVICE_CALLED = "service_called"
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

    def add_event(self, event_name: str, event_data: dict=None):
        self.add(EVENT, {
            "event": event_name,
            "event_data": event_data if event_data else {}
        })

    def add_error(self, error_msg: str):
        self.add(ERROR, {
            "message": error_msg
        })

    def get_logs(self):
        return self._log.copy()

    def set_max_logs(self, max_logs):
        self._max_logs = max_logs
        self._trim_log()

    def _trim_log(self):
        while len(self._log) > self._max_logs:
            del self._log[0]
