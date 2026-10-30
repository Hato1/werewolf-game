import logging
import typing
from enum import IntEnum


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    message = "%(levelname)s: %(message)s"

    FORMATS: typing.ClassVar = {
        logging.DEBUG: grey + message + reset,
        logging.INFO: grey + message + reset,
        logging.WARNING: yellow + message + reset,
        logging.ERROR: red + message + reset,
        logging.CRITICAL: bold_red + message + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


def initialize_logger(log_level: int | LogLevel = LogLevel.INFO):
    """Initialize the root logger with the specified log level.

    log_level: Hide logs below this level. Can be an int or a LogLevel.
    """
    # Setting root logger is bad practice, too bad!
    logger = logging.root
    logger.setLevel(log_level)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)
