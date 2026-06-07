"""Typed notification emitters. A handler receives an `Emit` callable that
writes a JSON-RPC notification frame to the transport.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from inclave_bridge.protocol import make_notification

# An Emit takes (method, params) and writes a notification frame.
Emit = Callable[[dict[str, Any]], None]


class EventEmitter:
    """Convenience wrapper that builds and sends the standard notifications."""

    def __init__(self, write: Emit) -> None:
        self._write = write

    def _send(self, method: str, params: dict[str, Any]) -> None:
        self._write(make_notification(method, params))

    # chat.* ---------------------------------------------------------------- #
    def chat_token(self, session_id: str, delta: str) -> None:
        self._send("chat.token", {"session_id": session_id, "delta": delta})

    def chat_message_done(self, session_id: str, role: str, content: str) -> None:
        self._send(
            "chat.message_done",
            {"session_id": session_id, "role": role, "content": content},
        )

    def chat_run_start(self, session_id: str, code: str) -> None:
        self._send("chat.run_start", {"session_id": session_id, "code": code})

    def chat_run_output(
        self,
        session_id: str,
        *,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_ms: int,
        timed_out: bool,
    ) -> None:
        self._send(
            "chat.run_output",
            {
                "session_id": session_id,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "timed_out": timed_out,
            },
        )

    def chat_turn_done(self, session_id: str, n_turns: int) -> None:
        self._send("chat.turn_done", {"session_id": session_id, "n_turns": n_turns})

    def chat_error(self, session_id: str, code: str, message: str) -> None:
        self._send(
            "chat.error",
            {"session_id": session_id, "code": code, "message": message},
        )

    # models.* -------------------------------------------------------------- #
    def models_pull_progress(self, name: str, status: str, completed: int, total: int) -> None:
        self._send(
            "models.pull_progress",
            {"name": name, "status": status, "completed": completed, "total": total},
        )

    # system.* -------------------------------------------------------------- #
    def ollama_state(self, running: bool) -> None:
        self._send("system.ollama_state", {"running": running})
