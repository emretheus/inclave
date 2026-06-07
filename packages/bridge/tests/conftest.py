from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ~/.inclave to a tmp dir for isolated config/sessions/workspace."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path
