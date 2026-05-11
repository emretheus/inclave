"""Operational logging — opt-in via `--debug`.

Privacy contract (PROJECT_PLAN §15.3): conversations are NEVER logged. This
module only emits structural events: command invocations, sandbox start/end,
ollama call attempt/failure, exit codes. Message content stays in memory.

Off by default. `setup_logging(debug=True)` installs a rotating file handler
at ~/.inclave/log/inclave.log (10 MB x 3). Calling it more than once is a
no-op so re-importing main during tests doesn't multiply handlers.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from inclave_core.config import log_dir

LOGGER_NAME = "inclave"
_LOG_FILENAME = "inclave.log"
_MAX_BYTES = 10 * 1024 * 1024
_BACKUPS = 3
_HANDLER_TAG = "inclave-file"


def get_logger() -> logging.Logger:
    """Return the package logger. Safe to call before setup_logging.

    Installs a NullHandler and disables propagation so that pre-setup log
    calls (e.g. during Typer callback wiring) don't surface through the root
    logger or `logging.lastResort` and pollute stderr.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.propagate = False
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    return logger


def setup_logging(*, debug: bool = False) -> logging.Logger:
    """Configure the package logger. Idempotent.

    debug=False  → WARNING level, no file handler (silent on the happy path).
    debug=True   → DEBUG level + rotating file at ~/.inclave/log/inclave.log.
    """
    logger = get_logger()
    logger.setLevel(logging.DEBUG if debug else logging.WARNING)
    logger.propagate = False

    if not debug:
        # Strip our handler (if a prior call installed one), keep the logger
        # quiet. Other handlers (test capture, etc.) are left alone.
        for h in list(logger.handlers):
            if getattr(h, "_inclave_tag", None) == _HANDLER_TAG:
                logger.removeHandler(h)
        return logger

    # Debug mode: ensure exactly one rotating handler at the log path.
    for h in logger.handlers:
        if getattr(h, "_inclave_tag", None) == _HANDLER_TAG:
            return logger

    path = log_dir() / _LOG_FILENAME
    handler = RotatingFileHandler(path, maxBytes=_MAX_BYTES, backupCount=_BACKUPS, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    # Tag so we can find and remove our own handler later without disturbing others.
    handler._inclave_tag = _HANDLER_TAG  # type: ignore[attr-defined]
    logger.addHandler(handler)
    return logger
