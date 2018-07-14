#!/usr/bin/env python3
import asyncio
import threading
import logging
import urllib.request
import sys

from ottoengine import engine, restapi, config
from ottoengine.fibers import clock

# Load the config
try:
    config = config.EngineConfig().load()
except Exception as e:
    print("Error encountered loading configuration file")
    print("{} {}".format(sys.exc_info()[0], sys.exc_info()[1]))
    sys.exit(1)

# Setup the logging
_LOG = logging.getLogger("run_otto")
logging.basicConfig(level=config.log_level)
fmt = ("%(levelname)s [%(name)s - %(funcName)s()] %(message)s")
colorfmt = "%(log_color)s{}%(reset)s".format(fmt)
# datefmt = '%y-%m-%d %H:%M:%S'

# Suppress overly verbose logs from libraries that aren't helpful
# logging.getLogger("requests").setLevel(logging.WARNING)
# logging.getLogger("urllib3").setLevel(logging.WARNING)
# logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

try:
    from colorlog import ColoredFormatter
    logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
        colorfmt,
        # datefmt=datefmt,
        reset=True,
        log_colors={
            'DEBUG': 'blue',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }
    ))
except ImportError:
    print("Failed to import colorlog module")
    sys.exit(1)

# Set Test Websocket to Start if needed
if len(sys.argv) > 1:
    if sys.argv[1].lower() == 'test':
        _LOG.info("Test Websocket server requested by command-line option")
        config.test_websocket_port = 8123

# Initialize the engine
loop = asyncio.get_event_loop()
# persistence_mgr = persistence.PersistenceManager(self, config.json_rules_dir)
clock = clock.EngineClock(config.tz, loop=loop)

engine = engine.OttoEngine(config, loop, clock)

# Start the Flask web server
_LOG.info("Starting web thread")
restapi.engine = engine
web_thread = threading.Thread(target=restapi.run_server)
web_thread.start()

# Start the engine's BaseLoop
engine.start_engine()

# Shutdown the webui
urllib.request.urlopen("http://localhost:{}/shutdown".format(config.rest_port))
