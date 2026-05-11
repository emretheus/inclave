"""Logging setup: off by default, installs rotating file handler in debug mode."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from inclave_core import get_logger, setup_logging
from inclave_core.logging import _HANDLER_TAG


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def _our_handlers(logger: logging.Logger) -> list[logging.Handler]:
    return [h for h in logger.handlers if getattr(h, "_inclave_tag", None) == _HANDLER_TAG]


def test_default_setup_is_silent(fake_home: Path) -> None:
    logger = setup_logging(debug=False)
    assert logger.level == logging.WARNING
    assert _our_handlers(logger) == []
    # No log file written by setup itself.
    assert not (fake_home / ".inclave" / "log" / "inclave.log").exists()


def test_debug_installs_file_handler(fake_home: Path) -> None:
    logger = setup_logging(debug=True)
    assert logger.level == logging.DEBUG
    handlers = _our_handlers(logger)
    assert len(handlers) == 1
    # Writing emits a log line to the rotated file.
    logger.debug("hello-debug")
    for h in handlers:
        h.flush()
    log_path = fake_home / ".inclave" / "log" / "inclave.log"
    assert log_path.exists()
    assert "hello-debug" in log_path.read_text(encoding="utf-8")


def test_debug_setup_is_idempotent(fake_home: Path) -> None:
    setup_logging(debug=True)
    setup_logging(debug=True)
    setup_logging(debug=True)
    assert len(_our_handlers(get_logger())) == 1


def test_toggling_back_removes_handler(fake_home: Path) -> None:
    setup_logging(debug=True)
    assert _our_handlers(get_logger())
    setup_logging(debug=False)
    assert _our_handlers(get_logger()) == []


def test_no_message_content_helper_available(fake_home: Path) -> None:
    """Privacy contract: get_logger() must return a real logger without
    requiring setup_logging first."""
    logger = get_logger()
    assert isinstance(logger, logging.Logger)


@pytest.fixture(autouse=True)
def _reset_logger() -> None:
    """Each test should start with a clean inclave logger."""
    logger = logging.getLogger("inclave")
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.setLevel(logging.NOTSET)
