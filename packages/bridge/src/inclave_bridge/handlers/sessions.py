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
    out: list[dict[str, Any]] = []
    for name, saved_at in list_sessions():
        sess = load_session(name)
        model = sess.model if sess else ""
        n_turns = sum(1 for m in sess.messages if m["role"] == "assistant") if sess else 0
        out.append(
            {
                "name": name,
                "saved_at": saved_at,
                "model": model,
                "n_turns": n_turns,
            }
        )
    return out


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
