import asyncio
import datetime
# import json
import logging
import signal
import sys
import traceback
# import typing

from ottoengine import clock, state, fibers, hass_websocket, dataobjects, const, persistence

ASYNC_TIMEOUT_SECS = 5

_LOG = logging.getLogger(__name__)
_LOG.setLevel(logging.DEBUG)


class OttoEngine(object):

    def __init__(self, hass_host, hass_port, hass_password, hass_ssl):
        self._hass_host = hass_host
        self._hass_port = hass_port
        self._hass_password = hass_password
        self._hass_ssl = hass_ssl
        # self._tzinfo = tzinfo

        self._loop = asyncio.get_event_loop()
        self._states = state.OttoEngineState()

        self._websocket = None
        self._fiber_websocket_reader = None
        self._clock = None

        self._state_listeners = {}     # Provide a way to lookup listeners by entity_id
        self._event_listeners = {}     # Provide a way to lookup listeners by event_type
        self._time_listeners = []      # Just keeps track of the IDs so we can remove during reload

    @property
    def states(self):
        return self._states

    #########################
    #    Private methods    #
    #########################

    def _stop_engine(self):
        '''Gracefully stop the engine'''
        self._fiber_websocket_reader.cancel()
        self._loop.stop()

    def _run_fiber(self, fiber) -> None:
        task = self.schedule_task(fiber.async_run())
        fiber.asyncio_task = task

    # def _add_event_listener(self, listener):
    #     _LOG.info("Adding event listener for entity: {} (rule: {})".format(listener.entity_id, listener.rule_id))
    #     # entry = { 'rule_id': rule_id, 'function': func }
    #     if listener.entity_id in self._event_listeners:
    #         self._event_listeners[listener.entity_id].append(listener)
    #     else:
    #         self._event_listeners[listener.entity_id] = [listener]

    #############################
    #    Private corroutines    #
    #############################

    async def _async_setup_engine(self):

        # Initialize the websocket
        self._websocket = hass_websocket.AsyncHassWebsocket(
            self._hass_host, self._hass_port, self._hass_password, self._hass_ssl
        )
        self._fiber_websocket_reader = fibers.FiberWebsocketReader(self, self._websocket)

        # Run the Websocket Reader Fiber
        self._run_fiber(self._fiber_websocket_reader)
        await asyncio.sleep(1)

        while not self._fiber_websocket_reader.connected:
            _LOG.info("Waiting for Websocket Fiber to connect")
            await asyncio.sleep(3)

        await self._websocket.async_subscribe_events(const.STATE_CHANGED)
        # await self._websocket.async_subscribe_events("call_service");
        await self._websocket.async_subscribe_events("timer_ended")
        await self._websocket.async_get_all_state()
        await self._websocket.async_get_all_services()

        # Start the EngineClock
        self._clock = clock.EngineClock(self._loop)
        self._run_fiber(self._clock)

        # Load the Automation Rules
        # await self._async_load_rules()
        await self._async_reload_rules()

    async def _async_load_rules(self):
        _LOG.info("Loading rules from persistence")
        persistence.engine = self

        rules = persistence.get_rules()
        for rule in rules:

            # Add State Listeners
            for listener in rule.get_state_listeners():
                _LOG.info(
                        "Adding state listener for entity: {} (rule: {})".format(
                            listener.entity_id, listener.rule_id))
                if listener.entity_id in self._state_listeners:
                    self._state_listeners[listener.entity_id].append(listener)
                else:
                    self._state_listeners[listener.entity_id] = [listener]

            # Add Event Listeners
            for listener in rule.get_event_listeners():
                _LOG.info(
                    "Adding event listener for event_type: {} (rule: {})".format(
                        listener.event_type, listener.rule_id))
                if listener.event_type in self._event_listeners:
                    self._event_listeners[listener.event_type].append(listener)
                else:
                    self._event_listeners[listener.event_type] = [listener]

            # Add Time Listeners
            for listener in rule.get_time_listeners():
                _LOG.info(
                    "Adding time listener: (rule: {}) {}".format(
                        listener.rule_id, listener.timepsec.serialize()))
                self._clock.add_timespec_action(
                    listener.listener_id, listener.trigger_function, listener.timepsec)
                self._time_listeners.append(listener.listener_id)

            # Add rule to State
            self.states.add_rule(rule)

    async def _async_clear_rules(self):
        _LOG.info("Clearing all registered state listeners")
        self._state_listeners = {}

        _LOG.info("Clearing all registered event listeners")
        self._event_listeners = {}

        _LOG.info("Clearing all registered time listeners")
        for listener_id in self._time_listeners:
            self._clock.remove_timespec_action(listener_id)
        self._time_listeners = []

        _LOG.info("Clearing all registered rules")
        self.states.clear_rules()

    async def _async_reload_rules(self):
        try:
            await self._async_clear_rules()
            await self._async_load_rules()
        except Exception as e:
            message = "Exception reloading rules: {}: {}".format(
                sys.exc_info()[0], sys.exc_info()[1])
            _LOG.error(message)
            traceback.print_exc()
            return {"success": False, "message": message}

        # print("{} rules loaded".format(len(self.states._rules)))
        # num_l = 0
        # for l in self._event_listeners.items():
        #     num_l += len(l)
        # print("{} event listeners".format(num_l))
        # num_l = 0
        # for l in self._clock._timeline:
        #     num_l += len(l.actions)
        # print("{} time  listeners".format(num_l))

        return {"success": True}

    async def _async_get_state(self, group, key):
        '''Correoutine to access state objects.  This must run in the event loop'''
        _LOG.debug("_async_get_state() called with - group: {}, key: {}".format(group, key))
        value = self._states.get_state(group, key)
        # Perhaps check that we are fetching a real state?
        return value

    async def _async_set_state(self, group, key, value):
        '''Correoutine to set state objects.  This must run in the event loop'''
        _LOG.debug(
            "_async_set_state() called with - group: {}, key: {}, value: {}".format(
                group, key, value))
        self._states.get_state(group, key, value)

    ###########################################################################
    #                          Engine's Public API                            #
    ###########################################################################

    def start_engine(self):
        '''Starts the Otto Engine until it is shutdown'''

        # Setup signal handlers
        self._loop.add_signal_handler(signal.SIGINT, self._stop_engine)
        self._loop.add_signal_handler(signal.SIGTERM, self._stop_engine)

        # Start the event loop
        try:
            _LOG.info("Starting event loop")
            self._loop.call_soon(
                self._states.set_engine_state, "start_time", datetime.datetime.now())
            self.schedule_task(self._async_setup_engine())
            self._loop.run_forever()
        finally:
            _LOG.info("Shutting down OttoEngine")
            self._loop.close()

    def process_event(self, event):
        ''' Process an event received by the websocket fiber '''
        if type(event) is dataobjects.StateChangedEvent:
            # Update the state
            self._states.set_entity_state(event.entity_id, event.new_state_obj)

            _LOG.debug("[Event] entity_id: {}, new_state: {}, attributes: {}".format(
                event.entity_id, event.new_state_obj.state, event.new_state_obj.attributes))

            # Trigger any listeners
            listeners = self._state_listeners.get(event.entity_id)
            if listeners is not None:
                for listener in listeners:
                    _LOG.info(
                        "Invoking trigger - rule: {}, entity: {}".format(
                            listener.rule_id, event.entity_id))
                    # The trigger_function is a reference to an async_handle_trigger() function
                    # created from AutomationRule.get_event_listeners()
                    self.schedule_task(listener.trigger_function(event))

        elif type(event) is dataobjects.HassEvent:

            _LOG.debug(
                "[Event] event_type: {}, event_data: {}".format(event.event_type, event.data_obj))

            # _LOG.warn("engine.process_event not implemented for event type: {}".format(event.event_type))
            listeners = self._event_listeners.get(event.event_type)
            if listeners is not None:
                for listener in listeners:
                    _LOG.info(
                        "Invoking trigger - rule: {}, event_type: {}".format(
                            listener.rule_id, event.event_type))
                    # The trigger_function is a reference to an async_handle_trigger() function
                    # created from AutomationRule.get_event_listeners()
                    self.schedule_task(listener.trigger_function(event))

    def get_state_threadsafe(self, group, key):
        '''Get state from engine.  This is called by threads outside of the event loop'''
        _LOG.debug("get_state() called with - group: {}, key: {}".format(group, key))
        future = asyncio.run_coroutine_threadsafe(self._async_get_state(group, key), self._loop)
        result = future.result(ASYNC_TIMEOUT_SECS)  # Wait for the result with a timeout
        return result

    def call_service_threadsafe(self, service_call):
        asyncio.run_coroutine_threadsafe(self.async_call_service(service_call), self._loop)

    async def async_call_service(self, service_call):
        await self._websocket.async_call_service(service_call)

    # ** Things outside the engine should not be setting state **
    #
    # def set_state_threadsafe(self, group, key, value):
    #     '''Set state from engine. This is called by threads outside of the envent loop'''
    #     _LOG.debug("set_state() called with - group: {}, key: {}, value: {}".format(group, key, value))
    #     future = asyncio.run_coroutine_threadsafe(self._async_set_state(group, key, value), self._loop)
    #     future.result(ASYNC_TIMEOUT_SECS)  # Wait for the result with a timeout

    def schedule_task(self, coro) -> asyncio.Task:
        return self._loop.create_task(coro)

    def get_rules(self) -> list:
        async def _async_get_rules():
            return self.states.get_rules()
        # future = asyncio.run_coroutine_threadsafe(async_get_rules(), self._loop)
        # return future.result(ASYNC_TIMEOUT_SECS)
        return asyncio.run_coroutine_threadsafe(
            _async_get_rules(), self._loop).result(ASYNC_TIMEOUT_SECS)

    def get_rule(self, rule_id) -> dict:
        async def _async_get_rule(rule_id):
            return self.states.get_rule(rule_id)
        return asyncio.run_coroutine_threadsafe(
            _async_get_rule(rule_id), self._loop).result(ASYNC_TIMEOUT_SECS)

    def save_rule(self, rule_dict):
        async def _async_save_rule(rule_dict):
            '''
            Returns { success: True } if successful,
            or { success: False, message: message } if unsuccessful.
            '''
            result = persistence.rule_from_dict(rule_dict)
            if not result.get("success"):
                return result

            rule = result.get("rule")
            try:
                persistence.save_rule(rule)
            except Exception as e:
                message = "Exception saving rule: {}: {}".format(
                    sys.exc_info()[0], sys.exc_info()[1])
                _LOG.error(message)
                traceback.print_exc()
                return {"success": False, "message": message}

            self.states.add_rule(rule)  # This will overwrite any previous rule with this ID
            return {"success": True}

        return asyncio.run_coroutine_threadsafe(
            _async_save_rule(rule_dict), self._loop).result(ASYNC_TIMEOUT_SECS)

    def delete_rule(self, rule_id) -> bool:
        async def _async_delete_rule(rule_id):
            return persistence.delete_rule(rule_id)
        return asyncio.run_coroutine_threadsafe(
            _async_delete_rule(rule_id), self._loop).result(ASYNC_TIMEOUT_SECS)

    def get_entities(self) -> list:
        async def _async_get_entites():
            return self.states.get_entities()

        future = asyncio.run_coroutine_threadsafe(_async_get_entites(), self._loop)
        return future.result(ASYNC_TIMEOUT_SECS)

    def get_services(self) -> list:
        async def _async_get_services():
            return self.states.get_services()

        future = asyncio.run_coroutine_threadsafe(_async_get_services(), self._loop)
        return future.result(ASYNC_TIMEOUT_SECS)

    def reload_rules(self) -> bool:
        # async def _async_reload_rules():
        #     try:
        #         await self._async_clear_rules()
        #         await self._async_load_rules()
        #     except Exception as e:
        #         message = "Exception reloading rules: {}: {}".format(sys.exc_info()[0], sys.exc_info()[1])
        #         _LOG.error(message)
        #         return { "success": False, "message": message }
        #     return { "success": True }

        future = asyncio.run_coroutine_threadsafe(self._async_reload_rules(), self._loop)
        return future.result(ASYNC_TIMEOUT_SECS)

    def websocket_fiber_ending(self):
        _LOG.warn("Websocket Fiber has ended...restarting Engine setup")
        self.schedule_task(self._async_setup_engine())

    def check_timespec(self, spec_dict):
        # async def _async_check_timespec(spec):
        try:
            spec = clock.TimeSpec.from_dict(spec_dict)
            next_time = spec.next_time_from_now().isoformat()
        except Exception as e:
            message = "Exception checking TimeSpec: {}".format(sys.exc_info()[1])
            message += " || Spec: {}".format(spec_dict)
            _LOG.error(message)
            return {"success": False, "message": message}
        return {"success": True, "next_time": next_time}
