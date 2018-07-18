
from ottoengine import helpers


def event_state_changed(id, entity_id: str, old_state: str, new_state: str):
    now = helpers.nowutc()
    event = {
        "id": id,
        "type": "event",
        "event": {
            "event_type": "state_changed",
            "data": {
                "entity_id": entity_id,
                "old_state": {
                    "entity_id": entity_id,
                    "state": old_state,
                    "attributes": {},
                    "last_changed": now.isoformat(),
                    "last_updated": now.isoformat()
                },
                "new_state": {
                    "entity_id": entity_id,
                    "state": new_state,
                    "attributes": {},
                    "last_changed": now.isoformat(),
                    "last_updated": now.isoformat()
                }
            },
            "origin": "LOCAL",
            "time_fired": now.isoformat()
        }
    }
    return event


def event_hass_event(id, event_type: str, event_data: str):
    now = helpers.nowutc()
    event = {
        "id": id,
        "type": "event",
        "event": {
            "event_type": event_type,
            "data": event_data,
            "origin": "LOCAL",
            "time_fired": now.isoformat()
        }
    }
    return event
