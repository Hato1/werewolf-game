"""Console logging with timestamps, colors and structured keyword context.

Usage:
    Call `initialize_logger()` once at program start (see `my_game.main`), then in
    every module create a logger with `get_logger(__name__)`:

        from my_game.core.logger import get_logger

        logger = get_logger(__name__)

        logger.info("Changing state", previous=old_state, next=new_state)
        logger.warning("Asset missing", path=path)
        logger.exception("Failed to load save", slot=3)

    Output (the logger name is right-aligned to the terminal edge):

        03:30:59 Changing state previous=MENU next=GAME        [my_game.core.state_manager]

Context:
    Any keyword argument other than `exc_info`, `stack_info` and `stacklevel` is
    treated as context. Context is printed as `key=value` (using `str()`) in the
    order it was passed, and is also attached to the `LogRecord`, so custom
    handlers can read it.
    Avoid keys that clash with built-in `LogRecord` attributes such as `name`,
    `message`, `args` or `module`; the standard library raises `KeyError` for those.

Messages also support standard lazy %-style arguments:

        logger.debug("Loaded %s assets", count)
"""

import logging
import re
import shutil
from collections.abc import MutableMapping
from enum import IntEnum
from typing import Any, ClassVar

# Attributes every LogRecord has; anything else on a record is user-supplied context.
_STANDARD_RECORD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
_TIME_FORMAT = "%H:%M:%S"


class LogLevel(IntEnum):
    """Log severities, mirroring the standard `logging` levels."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class CustomFormatter(logging.Formatter):
    """Format records as `HH:MM:SS message key=value ... [logger.name]`.

    The message is colored by severity, context in magenta, and the logger name
    in cyan, padded so it touches the right edge of the terminal.
    """

    CYAN = "\x1b[36;20m"
    MAGENTA = "\x1b[35;20m"
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    LEVEL_COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: GREY,
        logging.INFO: GREY,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, self.GREY)
        line = f"{self.formatTime(record, _TIME_FORMAT)} {color}{record.getMessage()}{self.RESET}"

        context = {key: value for key, value in record.__dict__.items() if key not in _STANDARD_RECORD_ATTRS}
        if context:
            context_text = " ".join(f"{key}={value}" for key, value in context.items())
            line += f" {self.MAGENTA}{context_text}{self.RESET}"

        # Pad using the visible width only, ignoring ANSI color codes.
        visible_width = len(_ANSI_ESCAPE.sub("", line))
        name_width = len(record.name) + 2  # Surrounding brackets.
        padding = max(1, shutil.get_terminal_size().columns - visible_width - name_width)
        line += f"{' ' * padding}[{self.CYAN}{record.name}{self.RESET}]"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        if record.stack_info:
            line += "\n" + self.formatStack(record.stack_info)
        return line


class ContextLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that accepts arbitrary keyword arguments as log context."""

    _STDLIB_KWARGS: ClassVar[frozenset[str]] = frozenset({"exc_info", "stack_info", "stacklevel"})

    def process(
        self,
        msg: Any,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """Move non-standard keyword arguments into `extra` so they land on the record."""
        extra: dict[str, Any] = dict(kwargs.pop("extra", None) or {})
        for key in tuple(kwargs):
            if key not in self._STDLIB_KWARGS:
                extra[key] = kwargs.pop(key)
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> ContextLoggerAdapter:
    """Return a logger that accepts keyword arguments as context.

    name: Logger name, normally `__name__`.
    """
    return ContextLoggerAdapter(logging.getLogger(name), {})


class _ConsoleHandler(logging.StreamHandler):
    """Marker subclass so `initialize_logger` can find its own handler."""


def initialize_logger(log_level: int | LogLevel = LogLevel.INFO) -> None:
    """Configure the root logger to print formatted logs to the console.

    Meant to be called once by the application entry point, not by library code.
    Safe to call again to change the level: the console handler is reused.

    log_level: Hide logs below this level. Can be an int or a LogLevel.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    handler = next((h for h in root_logger.handlers if isinstance(h, _ConsoleHandler)), None)
    if handler is None:
        handler = _ConsoleHandler()
        root_logger.addHandler(handler)

    handler.setLevel(log_level)
    handler.setFormatter(CustomFormatter())
