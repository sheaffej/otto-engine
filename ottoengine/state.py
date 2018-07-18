import copy
import logging

_LOG = logging.getLogger(__name__)


class OttoEngineState(object):

    def __init__(self):
        self._engine_states = {}
        self._entity_states = {}
        self._services_states = {}
        self._rules = {}

    # Generic
    def get_state(self, group, key):
        '''Returns a state value from the engine state'''
        if "engine" in group:
            return self._engine_states.get(key)
        if "entities" in group:
            return self._entities_states.get(key)
        if "services" in group:
            return self._services_states.get(key)
        return None

    def set_state(self, group, key, value):
        '''Sets a state value in the engine state'''
        _LOG.debug("set_state({}, {}, {})".format(group, key, value))
        if "engine" in group:
            self._engine_states[key] = value
        if "entities" in group:
            self._entities_states[key] = value
        if "services" in group:
            self._services_states[key] = value

    # Engine States
    def set_engine_state(self, key, value):
        _LOG.debug("set_engine_state({}, {})".format(key, value))
        self._engine_states[key] = value

    def get_engine_state(self, key):
        '''Returns an engine state value '''
        return self._engine_states.get(key)

    # Entity states
    def set_entity_state(self, entity_id, state_obj):
        '''Sets an entity state'''
        _LOG.debug("{} -> {}".format(entity_id, state_obj.state))
        self._entity_states[entity_id] = state_obj

    def get_entity_state(self, entity_id):
        '''Sets an entity state'''
        return self._entity_states.get(entity_id)

    def get_all_entity_state_copy(self):
        return copy.deepcopy(self._entity_states)

    def get_entities(self) -> list:
        return [
            {
                "entity_id": entity,
                "friendly_name": self._entity_states.get(entity).friendly_name,
                "hidden": self._entity_states[entity].hidden
            }
            for entity in self._entity_states.keys()
        ]

    # Services States
    def set_service_info(self, service_domain):
        _LOG.debug("set_service_info({})".format(service_domain))
        self._services_states[service_domain.name] = service_domain

    def get_service_info(self, service_domain_str):
        return self._services_states.get(service_domain_str)

    def get_services(self) -> list:
        return [service for service in self._services_states.values()]

    # Rule States
    def add_rule(self, rule):
        self._rules[rule.id] = rule

    def get_rule(self, rule_id):
        return self._rules.get(rule_id)

    def get_rules(self) -> list:
        return list(self._rules.values())

    def clear_rules(self):
        self._rules = {}
