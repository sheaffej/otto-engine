#!/usr/bin/env python3
import asyncio
import threading
import logging
import urllib.request
import sys

from ottoengine import engine, restapi, config, persistence, utils, enginelog
from ottoengine.fibers import clock

# Load the config
try:
    config = config.EngineConfig().load()
except Exception as e:
    print("Error encountered loading configuration file")
    print("{} {}".format(sys.exc_info()[0], sys.exc_info()[1]))
    sys.exit(1)

# Setup the logging
utils.setup_logging(config.log_level)
_LOG = logging.getLogger("run_otto")

# Set Test Websocket to Start if needed
if len(sys.argv) > 1:
    if sys.argv[1].lower() == 'test':
        _LOG.info("Test Websocket server requested by command-line option")
        config.test_websocket_port = 8123

# Initialize the engine
loop = asyncio.get_event_loop()
clock = clock.EngineClock(config.tz, loop=loop)
persistence_mgr = persistence.PersistenceManager(config.json_rules_dir)
engine_log = enginelog.EngineLog()

engine_obj = engine.OttoEngine(config, loop, clock, persistence_mgr, engine_log)

# Start the Flask web server
_LOG.info("Starting web thread")
restapi.engine_obj = engine_obj
web_thread = threading.Thread(target=restapi.run_server)
web_thread.start()

# Start the engine's BaseLoop
engine_obj.start_engine()

# Shutdown the webui
urllib.request.urlopen("http://localhost:{}/shutdown".format(config.rest_port))
