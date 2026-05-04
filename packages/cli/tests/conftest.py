"""Shared pytest fixtures for inclave-cli tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect Path.home() to a tmp dir so config writes don't touch the real home."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path
