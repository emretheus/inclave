"""JSON-RPC 2.0 server over stdio — the bridge sidecar entrypoint.

Reads newline-delimited JSON-RPC requests on stdin, writes responses and
streamed notifications on stdout. One request is handled at a time (the desktop
serializes user actions per session); streaming methods emit notifications
synchronously as they progress, then return a final result.

The server holds zero privileged logic of its own — it only routes to handlers,
which call the engine. The single trust boundary stays in the engine.
"""

from __future__ import annotations

import json
import sys
import threading
from collections.abc import Callable
from typing import Any, TextIO

from inclave_core import get_logger
from inclave_core.errors import (
    CLIError,
    ConfigError,
    InClaveError,
    OllamaError,
    OllamaUnavailableError,
    SandboxError,
)

from inclave_bridge import protocol
from inclave_bridge.events import EventEmitter
from inclave_bridge.handlers import chat as chat_h
from inclave_bridge.handlers import config as config_h
from inclave_bridge.handlers import files as files_h
from inclave_bridge.handlers import models as models_h
from inclave_bridge.handlers import sessions as sessions_h
from inclave_bridge.handlers import system as system_h
from inclave_bridge.store import SessionStore

log = get_logger()


def _error_data_code(exc: InClaveError) -> str:
    if isinstance(exc, OllamaUnavailableError):
        return protocol.ERR_OLLAMA_UNAVAILABLE
    if isinstance(exc, OllamaError):
        return protocol.ERR_OLLAMA
    if isinstance(exc, SandboxError):
        return protocol.ERR_SANDBOX
    if isinstance(exc, ConfigError):
        return protocol.ERR_CONFIG
    if isinstance(exc, CLIError):
        return protocol.ERR_NOT_FOUND
    return protocol.ERR_GENERIC


class BridgeServer:
    """Owns the dispatch table, the session store, and the write lock."""

    def __init__(self, out: TextIO | None = None) -> None:
        self._out = out or sys.stdout
        self._write_lock = threading.Lock()
        self._store = SessionStore()
        self._emitter = EventEmitter(self._write_frame)
        self._table = self._build_table()

    # ------------------------------------------------------------------ #
    # Wire I/O
    # ------------------------------------------------------------------ #
    def _write_frame(self, frame: dict[str, Any]) -> None:
        line = json.dumps(frame, ensure_ascii=False)
        with self._write_lock:
            self._out.write(line + "\n")
            self._out.flush()

    # ------------------------------------------------------------------ #
    # Dispatch table
    # ------------------------------------------------------------------ #
    def _build_table(self) -> dict[str, Callable[[dict[str, Any]], Any]]:
        e = self._emitter
        s = self._store
        return {
            "system.status": system_h.status,
            "ollama.ensure_running": system_h.ensure_running,
            "config.get": config_h.get,
            "config.set": config_h.set_,
            "models.list": models_h.list_,
            "models.remove": models_h.remove,
            "models.set_default": models_h.set_default_,
            "models.pull": lambda p: models_h.pull(p, e),
            "files.add": files_h.add,
            "files.list": files_h.list_,
            "files.remove": files_h.remove,
            "files.clear": files_h.clear,
            "sessions.list": sessions_h.list_,
            "sessions.load": sessions_h.load,
            "sessions.save": sessions_h.save,
            "sessions.delete": sessions_h.delete,
            "chat.send": lambda p: chat_h.send(p, e, s),
            "chat.run_last": lambda p: chat_h.run_last(p, e, s),
            "chat.cancel": lambda p: chat_h.cancel(p, e, s),
        }

    # ------------------------------------------------------------------ #
    # Request handling
    # ------------------------------------------------------------------ #
    def handle_obj(self, obj: dict[str, Any]) -> None:
        req = protocol.Request.from_obj(obj)
        handler = self._table.get(req.method)
        if handler is None:
            self._write_frame(
                protocol.make_error(
                    req.id,
                    protocol.METHOD_NOT_FOUND,
                    f"unknown method: {req.method}",
                )
            )
            return
        try:
            result = handler(req.params)
            # Notifications (no id) get no response frame.
            if req.id is not None:
                self._write_frame(protocol.make_response(req.id, result))
        except KeyError as exc:
            self._write_frame(
                protocol.make_error(
                    req.id,
                    protocol.INVALID_PARAMS,
                    f"missing param: {exc}",
                    protocol.ERR_GENERIC,
                )
            )
        except InClaveError as exc:
            self._write_frame(
                protocol.make_error(
                    req.id,
                    protocol.INTERNAL_ERROR,
                    str(exc),
                    _error_data_code(exc),
                )
            )
        except Exception as exc:  # pragma: no cover — last-resort guard
            log.exception("handler crashed: %s", req.method)
            self._write_frame(
                protocol.make_error(
                    req.id,
                    protocol.INTERNAL_ERROR,
                    f"{type(exc).__name__}: {exc}",
                    protocol.ERR_GENERIC,
                )
            )

    def handle_line(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            self._write_frame(
                protocol.make_error(None, protocol.PARSE_ERROR, f"parse error: {exc}")
            )
            return
        if not isinstance(obj, dict):
            self._write_frame(
                protocol.make_error(None, protocol.INVALID_REQUEST, "request must be an object")
            )
            return
        self.handle_obj(obj)

    def serve(self, stdin: TextIO | None = None) -> int:
        src = stdin or sys.stdin
        log.debug("bridge: serving on stdio")
        for line in src:
            self.handle_line(line)
        return 0


def main() -> int:
    return BridgeServer().serve()


if __name__ == "__main__":
    raise SystemExit(main())
