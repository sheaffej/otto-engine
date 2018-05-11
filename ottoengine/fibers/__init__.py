import logging
import traceback
from concurrent.futures import CancelledError

_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)


class Fiber(object):
    def __init__(self):
        self._running = True
        self.asyncio_task = None
        self._name = type(self).__name__

    async def async_run(self):
        _LOG.info("Fiber {} starting".format(type(self).__name__))
        try:
            await self._async_run()
        except (CancelledError, RuntimeError) as e:
            # I think only RuntimeError is needed
            # But the asyncio docs say that Task.cancel() will inject a CancelledError
            # into the coroutine
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
