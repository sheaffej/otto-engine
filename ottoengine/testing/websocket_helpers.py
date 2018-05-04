import datetime


def event_state_changed(id, entity_id, old_state, new_state):
    now = datetime.datetime.now()
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
