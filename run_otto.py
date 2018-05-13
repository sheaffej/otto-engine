#!/usr/bin/env python3
import threading
import logging
import urllib.request
import sys

from ottoengine import engine, restapi, config

# Load the config
try:
    config = config.EngineConfig()
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


# Initialize the engine
engine = engine.OttoEngine(config)

# Start the Flask web server
_LOG.info("Starting web thread")
restapi.engine = engine
web_thread = threading.Thread(target=restapi.run_server)
web_thread.start()

# Start the engine's BaseLoop
engine.start_engine()

# Shutdown the webui
urllib.request.urlopen("http://localhost:{}/shutdown".format(config.rest_port))
