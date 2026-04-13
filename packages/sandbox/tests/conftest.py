from pathlib import Path

import pytest


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """A clean per-test workdir, returned as an absolute path."""
    return tmp_path.resolve()
