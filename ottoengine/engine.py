import asyncio
import logging
import signal
import sys
import traceback

from ottoengine import state, const, persistence, config, helpers, enginelog, hass_websocket_client
from ottoengine.model import dataobjects, trigger_objects, rule_objects, action_objects
from ottoengine.fibers import clock, hass_websocket_reader
from ottoengine.testing import test_websocket


ASYNC_TIMEOUT_SECS = 5

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)


class OttoEngine(object):

    def __init__(self, config: config.EngineConfig,
                 loop: asyncio.AbstractEventLoop,
                 clock_obj: clock.EngineClock,
                 persistence_mgr: persistence.PersistenceManager,
                 enginelog: enginelog.EngineLog):

        self._config = config
        self._loop = loop
        self._persistence_mgr = persistence_mgr
        self._clock = clock_obj
        self._enginelog = enginelog

        self._websocket = None
        self._fiber_websocket_reader = None

        self._states = state.OttoEngineState()

        self._event_listeners = {}     # Provide a way to lookup listeners by event_type
        self._time_listeners = []     # Just keeps track of the IDs so we can remove during reload

    # ~~~~~~~~~~~~~~~~~~~~~~~~
    #   Engine's Public API
    # ~~~~~~~~~~~~~~~~~~~~~~~~

    @property
    def states(self):
        return self._states

    @property
    def englog(self):
        return self._enginelog

    def start_engine(self):
        '''Starts the Otto Engine until it is shutdown'''

        # Setup signal handlers
        self._loop.add_signal_handler(signal.SIGINT, self._stop_engine)
        self._loop.add_signal_handler(signal.SIGTERM, self._stop_engine)

        # Start the event loop
        try:
            _LOG.info("Starting event loop")
            self.englog.add_event("Otto-Engine starting")
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
                    _LOG.info("Invoking trigger: rule {}, entity: {}".format(
                            listener.rule.id, event.entity_id))
                    listeners.append(listener)

        elif isinstance(event, dataobjects.HassEvent):
            _LOG.debug(
                "[Event] event_type: {}, event_data: {}".format(event.event_type, event.data_obj))

            event_listeners = self._event_listeners.get(event.event_type)
            if event_listeners is not None:
                for listener in event_listeners:
                    _LOG.info("Invoking trigger: rule {}, event_type: {}".format(
                            listener.rule.id, event.event_type))
                    listeners.append(listener)

        # The trigger_function is a reference to an async_handle_trigger() function
        # created from rule_objects.get_XXX_listeners()
        for listener in listeners:
            self._loop.create_task(
                async_invoke_rule(self, listener.rule, trigger=listener.trigger, event=event))

    async def call_service(self, service_call: dataobjects.ServiceCall):
        await self._websocket.async_call_service(service_call)
        self.englog.add(enginelog.SERVICE_CALLED, service_call.serialize())

    def websocket_fiber_ending(self):
        _LOG.warn("Websocket Fiber has ended...restarting Engine setup")
        self._loop.create_task(self._async_setup_engine())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #                       Threadsafe methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # These are to be called by threads outside of the engine's event loop

    def get_state_threadsafe(self, group, key):
        return asyncio.run_coroutine_threadsafe(
            self._async_get_state(group, key), self._loop).result(ASYNC_TIMEOUT_SECS)

    def get_entity_state_threadsafe(self, entity_id):
        async def _async_get_entity_state():
            return self.states.get_entity_state(entity_id)
        return asyncio.run_coroutine_threadsafe(
            _async_get_entity_state(), self._loop).result(ASYNC_TIMEOUT_SECS)

    def get_all_entity_state_threadsafe(self):
        async def _async_get_all_entity_state():
            return self.states.get_all_entity_state_copy()
        return asyncio.run_coroutine_threadsafe(
            _async_get_all_entity_state(), self._loop).result(ASYNC_TIMEOUT_SECS)

    def get_rules_threadsafe(self) -> list:
        async def _async_get_rules():
            return self.states.get_rules()
        return asyncio.run_coroutine_threadsafe(
            _async_get_rules(), self._loop).result(ASYNC_TIMEOUT_SECS)

    def get_rule_threadsafe(self, rule_id) -> dict:
        async def _async_get_rule(rule_id):
            return self.states.get_rule(rule_id)
        return asyncio.run_coroutine_threadsafe(
            _async_get_rule(rule_id), self._loop).result(ASYNC_TIMEOUT_SECS)

    def delete_rule_threadsafe(self, rule_id) -> bool:
        async def _async_delete_rule(rule_id):
            return self._persistence_mgr.delete_rule(rule_id)
        return asyncio.run_coroutine_threadsafe(
            _async_delete_rule(rule_id), self._loop).result(ASYNC_TIMEOUT_SECS)

    def reload_rules_threadsafe(self) -> bool:
        return asyncio.run_coroutine_threadsafe(
            self._async_reload_rules(), self._loop).result(ASYNC_TIMEOUT_SECS)

    def get_entities_threadsafe(self) -> list:
        async def _async_get_entites():
            return self.states.get_entities()
        return asyncio.run_coroutine_threadsafe(
            _async_get_entites(), self._loop).result(ASYNC_TIMEOUT_SECS)

    def get_services_threadsafe(self) -> list:
        async def _async_get_services():
            return self.states.get_services()
        return asyncio.run_coroutine_threadsafe(
            _async_get_services(), self._loop).result(ASYNC_TIMEOUT_SECS)

    def get_logs_threadsafe(self) -> list:
        async def _async_get_logs():
            return self.englog.get_logs()
        return asyncio.run_coroutine_threadsafe(
            _async_get_logs(), self._loop).result(ASYNC_TIMEOUT_SECS)

    def save_rule_threadsafe(self, rule_dict):
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

    def check_timespec_threadsafe(self, spec_dict):
        try:
            spec = clock.TimeSpec.from_dict(spec_dict)
            next_time = spec.next_time_from(helpers.nowutc()).isoformat()
        except Exception as e:
            message = "Exception checking TimeSpec: {} ({})".format(spec_dict, sys.exc_info()[1])
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
            self._config.hass_token, self._config.hass_ssl
        )
        self._fiber_websocket_reader = hass_websocket_reader.HassWebSocketReader(
            self, self._websocket)

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
        _LOG.info("{} rules found in {}".format(len(rules), self._config.json_rules_dir))
        for rule in rules:
            await self._async_load_rule(rule)

    async def _async_load_rule(self, rule):
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

                    async def async_time_triggered(engine_obj=self):
                        await async_invoke_rule(engine_obj, rule, trigger=None, event=None),

                    self._clock.add_timespec_action(
                        listener.trigger.id,
                        async_time_triggered,
                        listener.trigger.timespec,
                        helpers.nowutc()
                    )
                    # Add reference so we can find the listener id to remove it
                    self._time_listeners.append(listener.trigger.id)

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


async def async_invoke_rule(engine_obj: OttoEngine, rule: rule_objects.AutomationRule,
                            trigger=None, event: dataobjects.HassEvent = None):
    _LOG.debug("invoke_rule called for rule {}".format(rule.id))

    if not rule.enabled:
        _LOG.debug("Rule {} is not enabled".format(rule.id))
        return

    # Evaluate Trigger
    if trigger is not None:
        if isinstance(trigger, trigger_objects.ListenerTrigger) and (event is not None):
            if trigger.eval_trigger(event):
                _LOG.debug("Rule {}'s trigger passed".format(rule.id))
                engine_obj.englog.add(enginelog.TRIGGER_FIRED, {
                    "trigger": trigger.serialize()
                })
            else:
                return  # This could happen a lot, so let's not log it
        else:
            _LOG.debug(
                "Trigger is not a ListenerTrigger, or event is None on rule: ".format(rule.id))

    # Evaluate Rule Condition
    _LOG.debug("Checking for rule {}'s rule condition".format(rule.id))
    if rule.rule_condition is not None:
        if rule.rule_condition.evaluate(engine_obj):
            _LOG.debug("Rule {}'s rule condition passed".format(rule.id))
            engine_obj.englog.add(enginelog.CONDITION_PASSED, {
                "rule": rule.id,
                "condition_type": "rule condition",
                "condition": rule.rule_condition.serialize()
            })
        else:
            _LOG.debug("Rule {}'s rule condition is false: {}".format(
                rule.id, rule.rule_condition.serialize()))
            return
    else:
        _LOG.debug("Rule {} does not have a rule condition".format(rule.id))

    # Run Actions
    _LOG.debug("Proceeding to run rule {}'s action sequences".format(rule.id))
    for seqId, action_seq in enumerate(rule.actions):
        _LOG.debug("Running rule {}'s action seq# {}".format(rule.id, seqId))

        if action_seq.action_condition is not None:
            _LOG.debug(
                "Checking rule {}'s action seq# {}'s action condition".format(rule.id, seqId))
            if action_seq.action_condition.evaluate(engine_obj):
                _LOG.debug(
                    "Rule {}'s action seq# {} action condition passed".format(rule.id, seqId))
                engine_obj.englog.add(enginelog.CONDITION_PASSED, {
                    "rule": rule.id,
                    "condition_type": "action condition",
                    "action_seq": seqId,
                    "condition": action_seq.action_condition.serialize()
                })

            else:
                _LOG.debug(
                    "Rule {}'s action seq# {}'s action condition is false "
                    + "(rule will not run): {}".format(
                        rule.id, seqId, action_seq.action_condition.serialize()))
                continue

        # Run the action sequence
        for actId, action in enumerate(action_seq.action_sequence):

            success = await action.async_execute(engine_obj)
            if not success:
                if isinstance(action, action_objects.ConditionAction):
                    _LOG.debug(
                        ("Rule {} aborting action seq# {} due to false "
                            + "condition at action# {}").format(rule.id, seqId, actId))
                else:
                    _LOG.error(
                        ("Rule {} aborting action seq# {} due to action "
                            + "failure at action# {}").format(rule.id, seqId, actId))
                return

        _LOG.debug("Rule {}'s action seq# {} complete".format(rule.id, seqId))

    _LOG.debug("Rule {} processing completed".format(rule.id))
    engine_obj.englog.add(enginelog.RULE_COMPLETED, {"rule": rule.id})
