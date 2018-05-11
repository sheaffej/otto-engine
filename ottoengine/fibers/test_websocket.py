import asyncio
import asyncws
import logging

from ottoengine.fibers import Fiber

_LOG = logging.getLogger(__name__)
_LOG.setLevel(logging.DEBUG)


class TestWebSocketServer(Fiber):
    def __init__(self, port):
        super().__init__()
        self._port = port
        self._clients = []  # List of websockets connected to this server
        self._clients_lock = asyncio.Lock()

    async def _async_run(self):
        try:
            await asyncws.start_server(self._echo, '127.0.0.1', self._port)
        except OSError as e:
            if e.errno == 48:
                _LOG.error(
                    "TestWebsocketServer not started. Port {} already in use".format(self._port))

    async def _echo(self, websocket: asyncws.Websocket):
        _LOG.info("Test websocket connected")
        # Register this new websocket with the list of client websockets
        with (await self._clients_lock):
            self._clients.append(websocket)

        try:
            while True:
                frame = await websocket.recv()
                _LOG.debug("Message is: {}".format(frame))
                if frame is None:
                    break

                # Refresh current list of clients
                with (await self._clients_lock):
                    clients_copy = list(self._clients)

                for client in clients_copy:
                        if client is websocket:
                            continue
                        await client.send(frame)

        except RuntimeError as e:
            _LOG.warn(str(e))

        finally:
            with (await self._clients_lock):
                self._clients.remove(websocket)
            _LOG.info("Test websocket closed")
