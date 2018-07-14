import asyncio
import logging
import signal
import sys
import traceback

from ottoengine.model import dataobjects, trigger_objects, rule_objects
from ottoengine import state, const, persistence, config, helpers
from ottoengine.fibers import clock, hass_websocket, hass_websocket_client, test_websocket
# from ottoengine.model.rule_objects import AutomationRule


ASYNC_TIMEOUT_SECS = 5

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)


class OttoEngine(object):

    def __init__(self, config: config.EngineConfig,
                 loop: asyncio.AbstractEventLoop,
                 clock_obj: clock.EngineClock,
                 persistence_mgr: persistence.PersistenceManager = None):

        self._config = config
        self._loop = loop
        self._persistence_mgr = persistence_mgr
        self._clock = clock_obj

        if not self._persistence_mgr:
            self._persistence_mgr = persistence.PersistenceManager(
                self, self._config.json_rules_dir)

        self._websocket = None
        self._fiber_websocket_reader = None

        self._states = state.OttoEngineState()

        # self._state_listeners = {}     # Provide a way to lookup listeners by entity_id
        self._event_listeners = {}     # Provide a way to lookup listeners by event_type
        self._time_listeners = []     # Just keeps track of the IDs so we can remove during reload

    # ~~~~~~~~~~~~~~~~~~~~~~~~
    #   Engine's Public API
    # ~~~~~~~~~~~~~~~~~~~~~~~~

    @property
    def states(self):
        return self._states

    def start_engine(self):
        '''Starts the Otto Engine until it is shutdown'''

        # Setup signal handlers
        self._loop.add_signal_handler(signal.SIGINT, self._stop_engine)
        self._loop.add_signal_handler(signal.SIGTERM, self._stop_engine)

        # Start the event loop
        try:
            _LOG.info("Starting event loop")
            self._loop.call_soon(
                self._states.set_engine_state, "start_time", helpers.nowutc())
            self._loop.create_task(self._async_setup_engine())
            self._loop.run_forever()
        finally:
            _LOG.info("Shutting down OttoEngine")
            self._loop.close()

    def process_event(self, event):
        ''' Process an event received by the websocket fiber '''

        listeners = []
        if isinstance(event, dataobjects.StateChangedEvent):
            # Update the state
            self._states.set_entity_state(event.entity_id, event.new_state_obj)

            _LOG.debug("[Event] entity_id: {}, new_state: {}, attributes: {}".format(
                event.entity_id, event.new_state_obj.state, event.new_state_obj.attributes))

            entity_listeners = self._event_listeners.get(event.entity_id)
            if entity_listeners is not None:
                for listener in entity_listeners:
                    _LOG.info("Invoking trigger - rule: {}, entity: {}".format(
                            listener.rule.id, event.entity_id))
                    listeners.append(listener)

        elif isinstance(event, dataobjects.HassEvent):
            _LOG.debug(
                "[Event] event_type: {}, event_data: {}".format(event.event_type, event.data_obj))

            event_listeners = self._event_listeners.get(event.event_type)
            if event_listeners is not None:
                for listener in event_listeners:
                    _LOG.info("Invoking trigger - rule: {}, event_type: {}".format(
                            listener.rule.id, event.event_type))
                    listeners.append(listener)

        # The trigger_function is a reference to an async_handle_trigger() function
        # created from rule_objects.get_XXX_listeners()
        for listener in listeners:
            # self._loop.create_task(listener.trigger_function(event, self._loop))
            self._loop.create_task(invoke_rule(self, listener.rule, listener.trigger, event=event))

    # async def _invoke_rule(self, rule: rule_objects.AutomationRule,
    #                        trigger, event: dataobjects.HassEvent = None):
    #     # Evaluate Trigger
    #     if isinstance(trigger, trigger_objects.ListenerTrigger) and (event is not None):
    #         if trigger.eval_trigger(event):
    #             _LOG.debug(
    #                 "Rule trigger passed. Scheduling rule condition check: {}".format(rule.id))
    #         else:
    #             return

    #     # Evaluate Rule Condition
    #     if rule.rule_condition.evaluate(self):
    #         _LOG.debug("Rule condition passed. Scheduling actions for rule: {}".format(rule.id))
    #     else:
    #         return

    #     # Run Actions
    #     for seqId, action_seq in enumerate(rule.actions):
    #         if action_seq.action_condition is not None:
    #             if action_seq.action_condition.evaluate(self):
    #                 await rule_objects.async_run_action_seq(rule, seqId, self)

    def get_state_threadsafe(self, group, key):
        '''Get state from engine.  This is called by threads outside of the event loop'''
        _LOG.debug("get_state() called with - group: {}, key: {}".format(group, key))
        future = asyncio.run_coroutine_threadsafe(self._async_get_state(group, key), self._loop)
        result = future.result(ASYNC_TIMEOUT_SECS)  # Wait for the result with a timeout
        return result

    def call_service_threadsafe(self, service_call):
        asyncio.run_coroutine_threadsafe(self.async_call_service(service_call), self._loop)

    def call_service(self, service_call):
        # await self._websocket.async_call_service(service_call)
        self._loop.create_task(self._websocket.async_call_service(service_call))

    def get_rules(self) -> list:
        async def _async_get_rules():
            return self.states.get_rules()
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
            result = self._persistence_mgr.rule_from_dict(rule_dict)
            if not result.get("success"):
                return result

            rule = result.get("rule")
            try:
                self._persistence_mgr.save_rule(rule)
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
            return self._persistence_mgr.delete_rule(rule_id)
        return asyncio.run_coroutine_threadsafe(
            _async_delete_rule(rule_id), self._loop).result(ASYNC_TIMEOUT_SECS)

    def reload_rules(self) -> bool:
        future = asyncio.run_coroutine_threadsafe(self._async_reload_rules(), self._loop)
        return future.result(ASYNC_TIMEOUT_SECS)

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

    def websocket_fiber_ending(self):
        _LOG.warn("Websocket Fiber has ended...restarting Engine setup")
        self._loop.create_task(self._async_setup_engine())

    def check_timespec(self, spec_dict):
        try:
            spec = clock.TimeSpec.from_dict(spec_dict)
            next_time = spec.next_time_from(helpers.nowutc()).isoformat()
        except Exception as e:
            message = "Exception checking TimeSpec: {}".format(sys.exc_info()[1])
            message += " || Spec: {}".format(spec_dict)
            _LOG.error(message)
            return {"success": False, "message": message}
        return {"success": True, "next_time": next_time}

    # ~~~~~~~~~~~~~~~~~~~~
    #   Private methods
    # ~~~~~~~~~~~~~~~~~~~~

    def _stop_engine(self):
        '''Gracefully stop the engine'''
        self._fiber_websocket_reader.cancel()
        self._loop.stop()

    def _run_fiber(self, fiber) -> None:
        task = self._loop.create_task(fiber.async_run())
        fiber.asyncio_task = task

    async def _async_setup_engine(self):

        # Start testing Websocket server
        if self._config.test_websocket_port:
            _LOG.info("Starting testing websocket server")
            self._run_fiber(test_websocket.TestWebSocketServer(self._config.test_websocket_port))

        # Initialize the websocket
        self._websocket = hass_websocket_client.AsyncHassWebsocket(
            self._config.hass_host, self._config.hass_port,
            self._config.hass_password, self._config.hass_ssl
        )
        self._fiber_websocket_reader = hass_websocket.HassWebSocketReader(self, self._websocket)

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
        self._run_fiber(self._clock)

        # Load the Automation Rules
        await self._async_reload_rules()

    async def _async_load_rules(self):
        _LOG.info("Loading rules from persistence")

        rules = self._persistence_mgr.get_rules(self._config.json_rules_dir)
        for rule in rules:
            # Register the rule's listeners
            self._load_listeners(rule)

            # Add rule to State
            self.states.add_rule(rule)

    def _load_listeners(self, rule: rule_objects.AutomationRule):
            for listener in rule_objects.get_listeners(rule):

                # State and Event triggers
                if isinstance(listener.trigger, trigger_objects.ListenerTrigger):
                    if isinstance(listener.trigger, trigger_objects.EventTrigger):
                        listener_id = listener.trigger.event_type
                    elif isinstance(listener.trigger,
                                    (trigger_objects.StateTrigger,
                                     trigger_objects.NumericStateTrigger)):
                        listener_id = listener.trigger.entity_id
                    _LOG.info("Adding listener for {} (rule: {})".format(listener_id, rule.id))
                    if listener_id in self._event_listeners:
                        self._event_listeners[listener_id].append(listener)
                    else:
                        self._event_listeners[listener_id] = [listener]

                # Time triggers
                if isinstance(listener.trigger, trigger_objects.TimeTrigger):
                    _LOG.info("Adding time listener: (rule: {}) {}".format(
                            listener.rule.id, listener.trigger.timespec.serialize()))

                    self._clock.add_timespec_action(
                        listener.trigger.id,
                        # listener.trigger.action_function,
                        invoke_rule(self, rule, listener.trigger, event=None),
                        listener.trigger.timespec,
                        helpers.nowutc()
                    )
                    # Add reference so we can find the listener id to remove it
                    self._time_listeners.append(listener.trigger.id)

            # # Add State Listeners
            # for listener in rule_objects.get_state_listeners(rule, self._loop):
            #     _LOG.info(
            #             "Adding state listener for entity: {} (rule: {})".format(
            #                 listener.entity_id, listener.rule_id))
            #     if listener.entity_id in self._state_listeners:
            #         self._state_listeners[listener.entity_id].append(listener)
            #     else:
            #         self._state_listeners[listener.entity_id] = [listener]

            # # Add Event Listeners
            # for listener in rule_objects.get_event_listeners(rule, self._loop):
            #     _LOG.info(
            #         "Adding event listener for event_type: {} (rule: {})".format(
            #             listener.event_type, listener.rule_id))
            #     if listener.event_type in self._event_listeners:
            #         self._event_listeners[listener.event_type].append(listener)
            #     else:
            #         self._event_listeners[listener.event_type] = [listener]

            # # Add Time Listeners
            # for listener in rule_objects.get_time_listeners(rule, self._loop):
            #     _LOG.info(
            #         "Adding time listener: (rule: {}) {}".format(
            #             listener.rule_id, listener.timepsec.serialize()))
            #     self._clock.add_timespec_action(
            #         listener.listener_id, listener.trigger_function,
            #         listener.timepsec, helpers.nowutc())
            #     self._time_listeners.append(listener.listener_id)

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


async def invoke_rule(engine: OttoEngine, rule: rule_objects.AutomationRule,
                      trigger, event: dataobjects.HassEvent = None):
    # Evaluate Trigger
    if trigger is not None:
        if isinstance(trigger, trigger_objects.ListenerTrigger) and (event is not None):
            if trigger.eval_trigger(event):
                _LOG.debug("Rule trigger passed: {}".format(rule.id))
            else:
                return

    # Evaluate Rule Condition
    if rule.rule_condition is not None:
        if rule.rule_condition.evaluate(engine):
            _LOG.debug("Rule condition passed: {}".format(rule.id))
        else:
            return

    # Run Actions
    for seqId, action_seq in enumerate(rule.actions):
        _LOG.debug("Running rule action seqence: {} #{}".format(rule.id, seqId))
        if action_seq.action_condition is not None:
            if action_seq.action_condition.evaluate(engine):
                _LOG.debug("Rule action condition passed: {} #{}".format(rule.id, seqId))
            else:
                _LOG.debug("Rule action condition failed: {} #{}".format(rule.id, seqId))
                return

        await rule_objects.async_run_action_seq(rule, seqId, engine)
        _LOG.debug("Rule action sequence complete: {} #{}".format(rule.id, seqId))
