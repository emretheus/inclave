"""Chat session persistence — autosave + resume.

Sessions are stored as JSON under ~/.inclave/sessions/:
  - last.json   — autosaved after every assistant turn
  - <name>.json — saved explicitly via /save <name> (named sessions)

Per PROJECT_PLAN §15.1 the privacy promise is: nothing leaves the machine, but
conversations CAN persist locally so users can resume. Disabling persistence
is a future config flag (save_history) — for v0.1 autosave is always on.

Schema is intentionally permissive: missing fields fall back to defaults so a
session saved by an older build still loads.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from inclave_core.config import sessions_dir
from inclave_core.errors import CLIError, ConfigError

SCHEMA_VERSION = 1
LAST = "last"


@dataclass
class Session:
    """A persisted chat session.

    `messages` matches the dicts passed to ollama.chat (`role`, `content`).
    `file_ids` is workspace file ids; on resume we look them up and skip any
    that have since been removed.
    """

    version: int = SCHEMA_VERSION
    model: str = ""
    workdir: str = ""
    file_ids: list[str] = field(default_factory=list)
    messages: list[dict[str, str]] = field(default_factory=list)
    saved_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "model": self.model,
            "workdir": self.workdir,
            "file_ids": list(self.file_ids),
            "messages": [dict(m) for m in self.messages],
            "saved_at": self.saved_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Session:
        version = data.get("version", SCHEMA_VERSION)
        s = cls(version=int(version) if isinstance(version, int) else SCHEMA_VERSION)
        m = data.get("model")
        if isinstance(m, str):
            s.model = m
        wd = data.get("workdir")
        if isinstance(wd, str):
            s.workdir = wd
        ids = data.get("file_ids")
        if isinstance(ids, list):
            s.file_ids = [str(x) for x in ids if isinstance(x, str)]
        msgs = data.get("messages")
        if isinstance(msgs, list):
            s.messages = [
                {"role": str(it["role"]), "content": str(it["content"])}
                for it in msgs
                if isinstance(it, dict) and "role" in it and "content" in it
            ]
        sa = data.get("saved_at")
        if isinstance(sa, str):
            s.saved_at = sa
        return s


def _session_path(name: str) -> Path:
    safe = name.strip()
    if not safe or "/" in safe or safe.startswith(".") or len(safe) > 60:
        raise CLIError(
            f"invalid session name: {name!r} "
            "(must be 1-60 chars, no slashes, must not start with a dot)"
        )
    return sessions_dir() / f"{safe}.json"


def save_session(session: Session, name: str = LAST) -> Path:
    """Write atomically to ~/.inclave/sessions/<name>.json. Returns the path."""
    session.saved_at = datetime.now(UTC).isoformat(timespec="seconds")
    path = _session_path(name)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


def load_session(name: str = LAST) -> Session | None:
    """Return the named session, or None if missing.

    Raises ConfigError if the file exists but is unreadable / malformed.
    """
    path = _session_path(name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise ConfigError(f"session {name!r} at {path} is unreadable: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"session {name!r} at {path} must be a JSON object")
    return Session.from_dict(data)


def list_sessions() -> list[tuple[str, str]]:
    """Return (name, saved_at) pairs, newest first. `last` always sorts to top
    if it exists; named sessions follow by saved_at descending.
    """
    root = sessions_dir()
    out: list[tuple[str, str]] = []
    last_entry: tuple[str, str] | None = None
    for p in root.glob("*.json"):
        name = p.stem
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        ts = data.get("saved_at", "") if isinstance(data, dict) else ""
        ts = ts if isinstance(ts, str) else ""
        if name == LAST:
            last_entry = (name, ts)
        else:
            out.append((name, ts))
    out.sort(key=lambda x: x[1], reverse=True)
    if last_entry is not None:
        out.insert(0, last_entry)
    return out
