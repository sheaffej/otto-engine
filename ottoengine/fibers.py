import asyncio
# import asyncws
import json
import logging
import traceback
from concurrent.futures import CancelledError

from ottoengine import hass_websocket, dataobjects, const

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)


class Fiber(object):
    def __init__(self):
        self._running = True
        self.asyncio_task = None
        self._name = type(self).__name__

    async def async_run(self):
        try:
            await self._async_run()
        except (CancelledError, RuntimeError) as e:
            # I think only RuntimeError is needed
            # But the asyncio docs say that Task.cancel() will inject a CancelledError into the coroutine
            _LOG.info("Fiber {} is shutting down [{}]".format(self._name, type(e).__name__))
        except Exception as e:
            traceback.print_exc()

    def cancel(self):
        self.asyncio_task.cancel()

    def stop(self):
        self._running = False

    # To be overridden by subclasses
    async def _async_run(self):
        pass

# class Fiber


class FiberWebsocketReader(Fiber):

    def __init__(self, engine, websocket):
        super().__init__()
        self._engine = engine
        self._socket = websocket
    
    @property
    def connected(self) -> bool:
        return self._socket.connected


    async def _async_run(self):
        _LOG.info("{} starting".format(type(self).__name__))

        # while self._running:

        # Connect the websocket
        await self._connect()

            # connected = await self._socket.async_connect()
            # while not connected:
            #     await asyncio.sleep(3)
            #     connected = await self._socket.async_connect()

            # while not self._websocket.authenticated:
            #     _LOG.debug("Websocket waiting for authentication")
            #     await asyncio.sleep(1)


            # await self._websocket.async_subscribe_events(const.STATE_CHANGED)
            # await self._websocket.async_subscribe_events("call_service");
            # await self._websocket.async_get_all_state()
            # await self._websocket.async_get_all_services()


        try:
            await self._read()
        except Exception as e:
            message = "Exception reading from websocket: {}".format(str(e))
            _LOG.error(message)
            # await self._wait_for_connection()

        await self._socket.async_close(force=True)
        self._engine.websocket_fiber_ending()
        




    async def _connect(self):
        # Wait until connected (does not need to be authenticated to read)
        # while not self._socket.connected:
        #     _LOG.debug("Websocket is not connected")
        #     await asyncio.sleep(3)
        connected = await self._socket.async_connect()
        while not connected:
            _LOG.debug("Websocket is not connected")
            await asyncio.sleep(3)
            connected = await self._socket.async_connect()
        _LOG.info("Websocket is connected")


    async def _read(self):
        while self._running and self._socket.connected:
            # try:
            raw_msg = await self._socket.async_receive()
            # except Exception as e:
                # _LOG.error("Exception reading from websocket: {}".format(str(e)))
                # continue

            if raw_msg is None:
                message = "websocket read was empty"
                _LOG.error(message)
                # continue
                raise Exception(message)

            _LOG.debug("Websocket read: {}".format(raw_msg))
            msg = json.loads(raw_msg)

            if "type" not in msg:
                _LOG.warning("Unknown response recieved on websocket:  {}".format(raw_msg))
                continue
            response_type = msg["type"]

            # Process the response

            if "auth_ok" in response_type:
                self._socket.set_authenticated(True)
                _LOG.debug("Websocket is authenticated")
            
            elif "result" in response_type:
                if not msg["success"]:
                    _LOG.warning("Websocket error response: {}".format(raw_msg))
                    continue
                
                msg_result = msg["result"]

                # States response
                if isinstance(msg_result, list):

                    for state_dict in msg_result:
                        state = dataobjects.EntityState(
                            state_dict[const.ENTITY_ID], 
                            state_dict[const.STATE], 
                            state_dict[const.ATTRIBUTES], 
                            state_dict[const.LAST_CHANGED],
                            state_dict.get("attributes").get("friendly_name"),
                            state_dict.get("attributes").get("hidden")
                        )

                        # Update state if it doesn't match the engine's state
                        existing_state = self._engine.states.get_entity_state(state.entity_id)

                        if not existing_state or not existing_state.is_equal(state):
                            self._engine.states.set_entity_state(state.entity_id, state)
                            _LOG.debug("Updating the engine's state for: {}".format(state.entity_id))
                        else:
                            # print("state has not changed")
                            pass
                    
                # Services response
                elif isinstance(msg_result, dict):

                    for domain_key in msg_result:
                        service_dicts = msg_result.get(domain_key)
                        service_domain = dataobjects.ServiceRegistration.from_websocket_dict(domain_key, service_dicts)
                        _LOG.debug("Registering service: {}".format(service_domain))
                        self._engine.states.set_service_info(service_domain)

            elif "pong" in response_type:
                _LOG.debug("Websocket PONG received")
                continue

            elif "event" in response_type:
                event_obj = msg.get("event")
                
                # State Changed Event
                if event_obj.get("event_type") in "state_changed":
                    event = dataobjects.StateChangedEvent.from_websocket_dict(event_obj)
                
                # Ignore: Call Service Event
                # elif event_obj.get("event_type") in "call_service":
                    # continue

                # Else it's something else
                else:
                    event = dataobjects.HassEvent.from_websocket_dict(event_obj)
                
                event.raw_msg = raw_msg
                self._engine.process_event(event)

# class FiberWebSocket


