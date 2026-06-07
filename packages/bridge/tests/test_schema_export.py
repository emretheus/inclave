"""Guard: the committed IPC schema.json must match what protocol.py produces.

If this fails, run:  uv run python packages/bridge/scripts/export_schema.py
and commit the regenerated packages-js/ipc-contract/schema.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from inclave_bridge.protocol import schema


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_committed_schema_is_fresh() -> None:
    committed_path = _repo_root() / "packages-js" / "ipc-contract" / "schema.json"
    assert committed_path.exists(), "schema.json missing — run export_schema.py"
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    assert committed == schema(), (
        "IPC schema is stale. Run: uv run python packages/bridge/scripts/export_schema.py"
    )
