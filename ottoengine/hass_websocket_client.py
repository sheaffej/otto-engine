# {"type": "auth", "api_password": "4password"}
# > {"type": "auth_ok", "ha_version": "0.41.0"}

# {"id": 1, "type": "subscribe_events", "event_type": "state_changed"}
# > {"id": 1, "type": "result", "success": true, "result": null}
# > {"id": 1, "type": "event", "event": {"event_type": "state_changed", "data": {"entity_id": "input_boolean.action_light", "old_state": {"entity_id": "input_boolean.action_light", "state": "on", "attributes": {}, "last_changed": "2017-05-06T01:08:38.324629+00:00", "last_updated": "2017-05-06T01:08:38.324629+00:00"}, "new_state": {"entity_id": "input_boolean.action_light", "state": "off", "attributes": {}, "last_changed": "2017-05-06T01:08:39.451397+00:00", "last_updated": "2017-05-06T01:08:39.451397+00:00"}}, "origin": "LOCAL", "time_fired": "2017-05-06T01:08:39.451411+00:00"}}


# {"id": 2, "type": "unsubscribe_events", "subscription": 1}
# > {"id": 2, "type": "result", "success": true, "result": null}


# {"id": 3, "type": "call_service", "domain": "input_boolean", "service": "toggle", "service_data": {"entity_id": "input_boolean.action_siren"}}
# > {"id": 3, "type": "result", "success": true, "result": null}

# {"id": 10, "type": "get_states"}
# > {"id": 10, "type": "result", "success": true, "result": [{"entity_id": "input_boolean.action_light", "state": "off", "attributes": {}, "last_changed": "2017-05-06T01:09:25.307187+00:00", "last_updated": "2017-05-06T01:09:25.307187+00:00"}, {"entity_id": "input_boolean.state_motion_in_home", "state": "off", "attributes": {}, "last_changed": "2017-05-06T01:04:26.578017+00:00", "last_updated": "2017-05-06T01:04:26.578017+00:00"}, {"entity_id": "input_boolean.action_siren", "state": "on", "attributes": {}, "last_changed": "2017-05-06T01:14:26.569892+00:00", "last_updated": "2017-05-06T01:14:26.569892+00:00"}, {"entity_id": "input_boolean.action_light2", "state": "off", "attributes": {}, "last_changed": "2017-05-06T01:04:26.578413+00:00", "last_updated": "2017-05-06T01:04:26.578413+00:00"}, {"entity_id": "input_boolean.action_siren2", "state": "off", "attributes": {}, "last_changed": "2017-05-06T01:04:26.578610+00:00", "last_updated": "2017-05-06T01:04:26.578610+00:00"}, {"entity_id": "input_boolean.state_home_occupied", "state": "on", "attributes": {}, "last_changed": "2017-05-06T01:04:26.578802+00:00", "last_updated": "2017-05-06T01:04:26.578802+00:00"}, {"entity_id": "automation.this_is_my_rule", "state": "off", "attributes": {"last_triggered": null, "friendly_name": "This is my rule"}, "last_changed": "2017-05-06T01:04:26.579000+00:00", "last_updated": "2017-05-06T01:04:26.579000+00:00"}, {"entity_id": "group.all_automations", "state": "off", "attributes": {"entity_id": ["automation.this_is_my_rule"], "order": 0, "auto": true, "friendly_name": "all automations", "hidden": true}, "last_changed": "2017-05-06T01:04:26.579682+00:00", "last_updated": "2017-05-06T01:04:26.579682+00:00"}]}

# {"id": 11, "type": "get_services"}
# > {"id": 11, "type": "result", "success": true, "result": {"homeassistant": {"turn_off": {"description": "", "fields": {}}, "turn_on": {"description": "", "fields": {}}, "toggle": {"description": "", "fields": {}}, "stop": {"description": "", "fields": {}}, "restart": {"description": "", "fields": {}}, "check_config": {"description": "", "fields": {}}, "reload_core_config": {"description": "", "fields": {}}}, "persistent_notification": {"create": {"description": "Show a notification in the frontend", "fields": {"message": {"description": "Message body of the notification. [Templates accepted]", "example": "Please check your configuration.yaml."}, "title": {"description": "Optional title for your notification. [Optional, Templates accepted]", "example": "Test notification"}, "notification_id": {"description": "Target ID of the notification, will replace a notification with the same Id. [Optional]", "example": 1234}}}}, "input_boolean": {"turn_off": {"description": "", "fields": {}}, "turn_on": {"description": "", "fields": {}}, "toggle": {"description": "", "fields": {}}}, "automation": {"trigger": {"description": "Trigger the action of an automation.", "fields": {"entity_id": {"description": "Name of the automation to trigger.", "example": "automation.notify_home"}}}, "reload": {"description": "Reload the automation configuration.", "fields": {}}, "toggle": {"description": "Toggle an automation.", "fields": {"entity_id": {"description": "Name of the automation to toggle on/off.", "example": "automation.notify_home"}}}, "turn_on": {"description": "Enable an automation.", "fields": {"entity_id": {"description": "Name of the automation to turn on.", "example": "automation.notify_home"}}}, "turn_off": {"description": "Disable an automation.", "fields": {"entity_id": {"description": "Name of the automation to turn off.", "example": "automation.notify_home"}}}}, "group": {"set_visibility": {"description": "Hide or show a group", "fields": {"entity_id": {"description": "Name(s) of entities to set value", "example": "group.travel"}, "visible": {"description": "True if group should be shown or False if it should be hidden.", "example": true}}}, "reload": {"description": "Reload group configuration.", "fields": {}}}, "logbook": {"log": {"description": "", "fields": {}}}}}

# {"id": 12, "type": "ping"}
# > {"id": 12, "type": "pong"}

import asyncws
import ssl
import json
import logging

EVENT_STATE_CHANGED = 'state_changed'

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)


class WebSocketError(Exception):
    '''Exeption class for websocket errors'''

    def __init__(self, message):
        super().__init__(message)


class AsyncHassWebsocket(object):

    def __init__(self, host, port, token=None, use_ssl=False):
        self._url = 'ws://{}:{}/api/websocket'.format(host, port)
        self._token = token
        self._use_ssl = use_ssl
        self._socket = None
        self._socket_connected = False
        self._socket_authenticated = False
        self._id = 0

    @property
    def connected(self):
        return self._socket_connected

    @property
    def authenticated(self):
        return self._socket_authenticated

    def set_authenticated(self, authenticated):
        self._socket_authenticated = authenticated

    async def async_connect(self) -> bool:
        '''
        Connects the websocket.

        Returns True if the connection was successful.

        If password is set, this method also submits the authentication request.
        However, the websocket reader will need to read the authentication response
        and mark the _socket_authenticated attribute True.
        This method returning True only means the websocket has connected,
        and does not mean that authentication was successful
        '''
        ssl_context = None
        if self._use_ssl:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            ssl_context.check_hostname = False

        try:
            self._socket = await asyncws.connect(self._url, ssl=ssl_context)
        except Exception as e:
            _LOG.error("Could not connect to websocket: {}".format(str(e)))
            return False

        if self._socket is None:
            return False
        self._socket_connected = True

        if self._token is not None:
            await self.async_authenticate()

        return True

    async def async_close(self, force=False):
        if force:
            self._socket.writer.close()
        else:
            self._socket.close()

    async def async_authenticate(self):
        '''
        Submits the password-based authentication request on the websocket.
        This method does not read the success/failure response.  That must
        be done by the websocket reader.
        '''
        await self._socket.send(json.dumps({"type": "auth", "access_token": self._token}))

    async def async_ping(self):
        '''Sends a ping message to the server'''
        if self._socket_authenticated:
            await self._socket.send(json.dumps({"id": self._nextid(), "type": "ping"}))

    async def async_subscribe_events(self, event_type):
        '''Subscribe to all events of type: event_type'''
        # event_type is optional.  If omitted, all events will be subscribed to
        _LOG.debug("Websocket subscribing to events of type: {}".format(event_type))
        await self._socket.send(
            json.dumps(
                {
                    'id': self._nextid(),
                    'type': 'subscribe_events',
                    'event_type': event_type
                }
            )
        )

    async def async_get_all_state(self):
        '''Retrieve all the state objects from Home Assistant.'''
        _LOG.debug("Websocket requesting all state from Home Assistant")
        await self._socket.send(
            json.dumps(
                {
                    'id': self._nextid(),
                    'type': 'get_states'
                }
            )
        )

    async def async_get_all_services(self):
        '''Retrieve all the services registered from Home Assistant.'''
        _LOG.debug("Websocket requesting all registered services from Home Assistant")
        await self._socket.send(
            json.dumps(
                {
                    'id': self._nextid(),
                    'type': 'get_services'
                }
            )
        )

    async def async_call_service(self, service_call_info):
        # {
        #     "id": 3,
        #     "type": "call_service",
        #     "domain": "input_boolean",
        #     "service": "toggle",
        #     "service_data": {
        #         "entity_id": "input_boolean.action_siren"
        #     }
        # }
        _LOG = logging.getLogger(f"{__name__}.async_call_service")
        _LOG.setLevel(logging.DEBUG)
        _LOG.debug("Websocket calling service: {}.{} with {}".format(
            service_call_info.domain, service_call_info.service, service_call_info.service_data)
        )
        await self._socket.send(
            json.dumps(
                {
                    'id': self._nextid(),
                    'type': 'call_service',
                    'domain': service_call_info.domain,
                    'service': service_call_info.service,
                    'service_data': service_call_info.service_data
                }
            )
        )

    async def async_receive(self) -> str:
        '''Receive a message from the websocket'''
        message = await self._socket.recv()
        _LOG.debug("Websocket read: {}".format(message))
        return message

    def _nextid(self):
        '''Return the next request ID to use'''
        self._id += 1
        return self._id
