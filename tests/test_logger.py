import io
import logging
import os
import re

import my_game.core.logger as logger_module
from my_game.core.logger import CustomFormatter, get_logger


def test_custom_formatter_right_aligns_colored_logger_name(monkeypatch) -> None:
    monkeypatch.setattr(logger_module.shutil, "get_terminal_size", lambda: os.terminal_size((80, 24)))
    record = logging.LogRecord(
        name="my_game.test",
        level=logging.INFO,
        pathname="/project/game.py",
        lineno=42,
        msg="Loaded %s players",
        args=(5,),
        exc_info=None,
        func="load_players",
    )

    formatted = CustomFormatter().format(record)

    formatted = re.sub(r"\x1b\[[0-9;]*m", "", formatted)

    assert len(formatted) == 80
    assert re.match(r"\d{2}:\d{2}:\d{2} Loaded 5 players", formatted)
    assert formatted.endswith("[my_game.test]")
    assert "\x1b[36;20m" in CustomFormatter().format(record)


def test_logger_accepts_arbitrary_keyword_context(monkeypatch) -> None:
    monkeypatch.setattr(logger_module.shutil, "get_terminal_size", lambda: os.terminal_size((80, 24)))
    output = io.StringIO()
    logger = get_logger("my_game.test.context")
    handler = logging.StreamHandler(output)
    handler.setFormatter(CustomFormatter())
    underlying_logger = logger.logger
    previous_level = underlying_logger.level
    previous_propagate = underlying_logger.propagate
    underlying_logger.setLevel(logging.INFO)
    underlying_logger.propagate = False
    underlying_logger.addHandler(handler)

    try:
        logger.info("Changing state", abc="active")
    finally:
        underlying_logger.removeHandler(handler)
        underlying_logger.setLevel(previous_level)
        underlying_logger.propagate = previous_propagate

    raw_formatted = output.getvalue()
    assert "\x1b[35;20m" in raw_formatted
    formatted = re.sub(r"\x1b\[[0-9;]*m", "", raw_formatted).strip()
    assert len(formatted) == 80
    assert re.match(r"\d{2}:\d{2}:\d{2} Changing state abc=active", formatted)
    assert formatted.endswith("[my_game.test.context]")


def test_context_keeps_kwarg_order_and_exception_is_appended(monkeypatch) -> None:
    monkeypatch.setattr(logger_module.shutil, "get_terminal_size", lambda: os.terminal_size((80, 24)))
    logger = get_logger("my_game.test.order")
    record = None

    class Capture(logging.Handler):
        def emit(self, rec: logging.LogRecord) -> None:
            nonlocal record
            record = rec

    handler = Capture()
    logger.logger.addHandler(handler)
    logger.logger.setLevel(logging.INFO)
    try:
        try:
            raise ValueError("boom")
        except ValueError:
            logger.exception("Failed", zeta=1, alpha=2)
    finally:
        logger.logger.removeHandler(handler)

    assert record is not None
    lines = re.sub(r"\x1b\[[0-9;]*m", "", CustomFormatter().format(record)).splitlines()
    assert len(lines[0]) == 80
    assert "Failed zeta=1 alpha=2" in lines[0]
    assert lines[-1] == "ValueError: boom"
