"""Export the IPC contract to JSON for TypeScript generation.

Run from the repo root:

    uv run python packages/bridge/scripts/export_schema.py

Writes packages-js/ipc-contract/schema.json. The TS generator (pnpm gen:ipc)
consumes this file. CI regenerates and diffs to catch drift.
"""

from __future__ import annotations

import json
from pathlib import Path

from inclave_bridge.protocol import schema


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    out = repo_root / "packages-js" / "ipc-contract" / "schema.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
