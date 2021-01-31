import logging
import traceback
import sys


def setup_logging(log_level):
    logging.basicConfig(level=log_level)
    fmt = ("%(asctime)s %(levelname)s [%(name)s.%(funcName)s()] %(message)s")
    colorfmt = "%(log_color)s{}%(reset)s".format(fmt)

    # Suppress overly verbose logs from libraries that aren't helpful
    # logging.getLogger("requests").setLevel(logging.WARNING)

    try:
        from colorlog import ColoredFormatter
        logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
            colorfmt,
            # datefmt='%y-%m-%d %H:%M:%S',
            reset=True,
            log_colors={
                'DEBUG': 'blue',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        ))
    except ImportError:  # pragma: no cover
        print("Failed to import colorlog module...exiting")
        traceback.print_exc()
        sys.exit(1)


def setup_debug_logging():
    setup_logging(logging.DEBUG)
    logging.getLogger().debug("Debug logging configured")
