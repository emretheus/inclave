"""sessions.* handlers."""

from __future__ import annotations

from typing import Any

from inclave_core import (
    Session,
    delete_session,
    list_sessions,
    load_session,
    save_session,
)
from inclave_core.errors import CLIError

from inclave_bridge import serialize


def list_(params: dict[str, Any]) -> list[dict[str, Any]]:
    # list_sessions() returns SessionSummary objects with everything we need,
    # so there's no need to re-load each session here.
    return [
        {
            "name": s.name,
            "saved_at": s.saved_at,
            "model": s.model,
            "n_turns": s.turns,
        }
        for s in list_sessions()
    ]


def load(params: dict[str, Any]) -> dict[str, Any]:
    name = str(params["name"])
    sess = load_session(name)
    if sess is None:
        raise CLIError(f"no session named {name!r}")
    return serialize.session(sess)


def save(params: dict[str, Any]) -> dict[str, Any]:
    name = str(params["name"])
    data = params["session"]
    sess = Session.from_dict(data)
    path = save_session(sess, name)
    return {"saved": True, "path": str(path)}


def delete(params: dict[str, Any]) -> dict[str, Any]:
    name = str(params["name"])
    removed = delete_session(name)
    return {"deleted": removed}
