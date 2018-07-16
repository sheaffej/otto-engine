import dateutil.parser
import logging

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)


class HassEvent(object):
    # "event": {
    #     "event_type": "call_service",
    #     "data": {
    #         "domain": "john",
    #         "service": "sheaffer"
    #     },
    #     "origin": "REMOTE",
    #     "time_fired": "2017-05-28T18:34:51.749350+00:00"
    # }

    def __init__(self, event_type, data_obj, time_fired):
        self.event_type = event_type
        self.data_obj = data_obj
        self.time_fired = time_fired

    @staticmethod
    def from_websocket_dict(response_dict):
        event_type = response_dict.get("event_type")
        data = response_dict["data"]
        time_fired = dateutil.parser.parse(response_dict["time_fired"])
        return HassEvent(event_type, data, time_fired)


class StateChangedEvent(HassEvent):
    #   "event": {
    #     "event_type": "state_changed",
    #     "data": {
    #       "entity_id": "input_boolean.action_light",
    #       "old_state": {
    #         "entity_id": "input_boolean.action_light",
    #         "state": "on",
    #         "attributes": {},
    #         "last_changed": "2017-05-06T01:08:38.324629+00:00",
    #         "last_updated": "2017-05-06T01:08:38.324629+00:00"
    #       },
    #       "new_state": {
    #         "entity_id": "input_boolean.action_light",
    #         "state": "off",
    #         "attributes": {},
    #         "last_changed": "2017-05-06T01:08:39.451397+00:00",
    #         "last_updated": "2017-05-06T01:08:39.451397+00:00"
    #       }
    #     },
    #     "origin": "LOCAL",
    #     "time_fired": "2017-05-06T01:08:39.451411+00:00"
    #   }

    def __init__(self, entity_id, old_state_obj, new_state_obj, time_fired):
        super().__init__(event_type="state_changed", data_obj=None, time_fired=time_fired)
        self.entity_id = entity_id
        self.old_state_obj = old_state_obj
        self.new_state_obj = new_state_obj

    @staticmethod
    def from_websocket_dict(response_dict):
        data = response_dict["data"]

        time_fired = dateutil.parser.parse(response_dict["time_fired"])
        entity_id = data["entity_id"]

        old_state_value = data["old_state"]["state"]
        old_attributes = data["old_state"]["attributes"]
        old_last_changed = dateutil.parser.parse(data["old_state"]["last_changed"])
        old_state_obj = EntityState(entity_id, old_state_value, old_attributes, old_last_changed)

        new_state_value = data["new_state"]["state"]
        new_attributes = data["new_state"]["attributes"]
        new_last_changed = dateutil.parser.parse(data["new_state"]["last_changed"])
        new_state_obj = EntityState(entity_id, new_state_value, new_attributes, new_last_changed)

        return StateChangedEvent(entity_id, old_state_obj, new_state_obj, time_fired)


class EntityState(object):
    # {
    #   "entity_id": "group.all_automations",
    #   "state": "off",
    #   "attributes": {
    #     "entity_id": [
    #       "automation.this_is_my_rule"
    #     ],
    #     "order": 0,
    #     "auto": true,
    #     "friendly_name": "all automations",
    #     "hidden": true
    #   },
    #   "last_changed": "2017-05-06T01:04:26.579682+00:00",
    #   "last_updated": "2017-05-06T01:04:26.579682+00:00"
    # }

    def __init__(
        self, entity_id, state, attributes,
        last_changed, friendly_name=None, hidden=False
    ):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes
        self.last_changed = last_changed
        self.friendly_name = friendly_name

        if (hidden is None):
            self.hidden = False
        else:
            self.hidden = hidden

    def is_equal(self, state):
        if type(self) != type(state):
            return False
        if self.entity_id != state.entity_id:
            return False
        if self.state != state.state:
            return False
        if self.last_changed != state.last_changed:
            return False
        return True


class ServiceRegistration(object):
    # "persistent_notification": {
    #     "create": {
    #       "description": "Show a notification in the frontend",
    #       "fields": {
    #         "message": {
    #           "description": "Message body of the notification.",
    #           "example": "Please check your configuration.yaml."
    #         },
    #         "title": {
    #           "description": "Optional title for your notification. [Optional]",
    #           "example": "Test notification"
    #         },
    #         "notification_id": {
    #           "description": "Target ID of the notification [Optional]",
    #           "example": 1234
    #         }
    #       }
    #     }
    #   },

    def __init__(self, domain):
        self.name = domain
        self.services = []

    def add_service(self, service):
        self.services.append(service)

    def __repr__(self):
        svc_names = []
        for svc in self.services:
            svc_names.append(" {}".format(svc.name))
        svc_str = ''.join(svc_names)

        return "<ServiceDomain object ({}):{}>".format(self.name, svc_str)

    @staticmethod
    def from_websocket_dict(domain_name, services_dict):
        '''Constructs a Service Domain from the dictionary description from a websocket'''
        domain = ServiceRegistration(domain_name)

        # Create ServiceCommands
        for key in services_dict.keys():
            service_name = key
            service_info = services_dict.get(key)

            _LOG.info("Found service: {}.{}".format(domain.name, service_name))

            service_description = service_info.get("description")

            service = Service(domain.name, service_name, service_description)

            for field_name, field_info in service_info.get("fields").items():

                if (type(field_info) is dict):
                    field_description = field_info.get("description")
                    field_example = field_info.get("example")
                else:
                    field_description = None
                    field_example = None

                service.add_field(ServiceField(field_name, field_description, field_example))

            domain.add_service(service)

        return domain

    def serialize(self) -> str:
        j = {
            "domain": self.name,
            "services": []
        }
        for s in self.services:
            j["services"].append(s.serialize())

        return j


class Service(object):
    #     "create": {
    #       "description": "Show a notification in the frontend",
    #       "fields": {
    #         "message": {
    #           "description": "Message body of the notification. [Templates accepted]",
    #           "example": "Please check your configuration.yaml."
    #         },
    #         "title": {
    #           "description": "Optional title for your notification. [Optional]",
    #           "example": "Test notification"
    #         },
    #         "notification_id": {
    #           "description": "Target ID of the notification [Optional]",
    #           "example": 1234
    #         }
    #       }
    #     }

    def __init__(self, domain, name, description):
        self._domain = domain
        self.name = name
        self.description = description
        self.fields = []

    def add_field(self, field):
        self.fields.append(field)

    def serialize(self) -> str:
        j = {
            "domain": self._domain,
            "service": self.name,
            "description": self.description,
            "fields": []
        }
        for f in self.fields:
            j["fields"].append(f.serialize())

        return j


class ServiceField(object):
    #         "message": {
    #           "description": "Message body of the notification. [Templates accepted]",
    #           "example": "Please check your configuration.yaml."
    #         },

    def __init__(self, name, description, example):
        self.name = name
        self.description = description
        self.example = example

    def serialize(self) -> str:
        j = {
            "name": self.name,
            "description": self.description,
            "example": self.example
        }
        return j


class ServiceCall(object):
    # Command to websocket
    # {
    #     "id": 3,
    #     "type": "call_service",
    #     "domain": "input_boolean",
    #     "service": "toggle",
    #     "service_data": {
    #         "entity_id": "input_boolean.action_siren"
    #     }
    # }

    def __init__(self, domain, service, service_data_dict):
        '''Creates a ServiceCall object.

        Field: service_data_dict can be {} or None
        '''
        self.domain = domain                    # i.e. input_boolean
        self.service = service                  # i.e. toggle
        self.service_data = service_data_dict   # fields: {entity_id:value, visible:True}

        if self.service_data is None:
            self.service_data = {}

    def serialize(self):
        return {
            "domain": self.domain,
            "service": self.service,
            "service_data": self.service_data
        }
