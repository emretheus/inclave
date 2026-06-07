"""The IPC contract — single source of truth for Rust, Python, and TypeScript.

Every request method, its params, its result, and every streamed event is
described here as plain data (TypedDict-ish dataclasses + a method registry).
`scripts/export_schema.py` serializes `METHODS` and `EVENTS` to JSON, which
generates the TypeScript zod schemas in `packages-js/ipc-contract`.

Keeping the contract declarative (not just code) is what stops the three
languages from drifting: the generated TS and the Python handlers both derive
from this file, and CI fails if the committed generated output is stale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# JSON-RPC reserved + InClave-specific error codes. The negative codes follow
# the JSON-RPC spec; the positive ones map the InClaveError hierarchy.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Domain error codes (string `data.code` on the JSON-RPC error object).
ERR_OLLAMA_UNAVAILABLE = "ollama_unavailable"
ERR_OLLAMA = "ollama_error"
ERR_SANDBOX = "sandbox_error"
ERR_CONFIG = "config_error"
ERR_NOT_FOUND = "not_found"
ERR_GENERIC = "error"


@dataclass(frozen=True)
class MethodSpec:
    """A request method the frontend can invoke."""

    name: str
    params: dict[str, str]  # name -> json type ("string","string[]","int","bool","object","null")
    returns: str  # json type description, or "stream" for streamed methods
    streams: bool = False  # True if it emits notifications during execution
    description: str = ""


@dataclass(frozen=True)
class EventSpec:
    """A notification the sidecar emits (no id)."""

    name: str
    payload: dict[str, str]
    description: str = ""


# --------------------------------------------------------------------------- #
# Methods (frontend -> sidecar)
# --------------------------------------------------------------------------- #

METHODS: list[MethodSpec] = [
    MethodSpec(
        "system.status",
        {},
        "object",
        description="Ollama running? default model? RAM? sandbox available?",
    ),
    MethodSpec(
        "config.get",
        {},
        "object",
        description="Return the full InClaveConfig.",
    ),
    MethodSpec(
        "config.set",
        {"key": "string", "value": "string"},
        "object",
        description="Set one config key, persist, return the new config.",
    ),
    MethodSpec(
        "models.list",
        {},
        "object[]",
        description="List locally installed Ollama models (+ VRAM compatibility).",
    ),
    MethodSpec(
        "models.pull",
        {"name": "string"},
        "stream",
        streams=True,
        description="Pull a model; emits models.pull_progress notifications.",
    ),
    MethodSpec(
        "models.remove",
        {"name": "string"},
        "object",
        description="Delete a local model.",
    ),
    MethodSpec(
        "models.set_default",
        {"name": "string"},
        "object",
        description="Set the default model in config.",
    ),
    MethodSpec(
        "files.add",
        {"paths": "string[]"},
        "object[]",
        description="Copy files into the workspace; return their FileEntry records.",
    ),
    MethodSpec(
        "files.list",
        {},
        "object[]",
        description="List workspace files.",
    ),
    MethodSpec(
        "files.remove",
        {"ref": "string"},
        "object",
        description="Remove a workspace file by id or name.",
    ),
    MethodSpec(
        "files.clear",
        {},
        "object",
        description="Remove every workspace file; returns count removed.",
    ),
    MethodSpec(
        "sessions.list",
        {},
        "object[]",
        description="List saved sessions (name, saved_at, model, n_turns).",
    ),
    MethodSpec(
        "sessions.load",
        {"name": "string"},
        "object",
        description="Load a session by name.",
    ),
    MethodSpec(
        "sessions.save",
        {"name": "string", "session": "object"},
        "object",
        description="Save a session under a name.",
    ),
    MethodSpec(
        "sessions.delete",
        {"name": "string"},
        "object",
        description="Delete a saved session.",
    ),
    MethodSpec(
        "chat.send",
        {"session_id": "string", "text": "string", "file_ids": "string[]"},
        "stream",
        streams=True,
        description="Run a full chat turn (stream + auto-run loop). Emits chat.* events.",
    ),
    MethodSpec(
        "chat.run_last",
        {"session_id": "string"},
        "stream",
        streams=True,
        description="Re-run the most recent python block (the /run escape hatch).",
    ),
    MethodSpec(
        "chat.cancel",
        {"session_id": "string"},
        "object",
        description="Request cancellation of an in-flight turn.",
    ),
    MethodSpec(
        "ollama.ensure_running",
        {},
        "object",
        description="Best-effort: confirm/launch the local Ollama daemon.",
    ),
]


# --------------------------------------------------------------------------- #
# Events (sidecar -> frontend, no id)
# --------------------------------------------------------------------------- #

EVENTS: list[EventSpec] = [
    EventSpec(
        "chat.token",
        {"session_id": "string", "delta": "string"},
        "A streamed chunk of the assistant reply.",
    ),
    EventSpec(
        "chat.message_done",
        {"session_id": "string", "role": "string", "content": "string"},
        "A full assistant message was committed.",
    ),
    EventSpec(
        "chat.run_start",
        {"session_id": "string", "code": "string"},
        "A python block is about to run in the sandbox.",
    ),
    EventSpec(
        "chat.run_output",
        {
            "session_id": "string",
            "stdout": "string",
            "stderr": "string",
            "exit_code": "int",
            "duration_ms": "int",
            "timed_out": "bool",
        },
        "The sandbox finished running a block.",
    ),
    EventSpec(
        "chat.turn_done",
        {"session_id": "string", "n_turns": "int"},
        "The whole turn (incl. auto-run loop) completed.",
    ),
    EventSpec(
        "chat.error",
        {"session_id": "string", "code": "string", "message": "string"},
        "A recoverable error during a turn.",
    ),
    EventSpec(
        "models.pull_progress",
        {"name": "string", "status": "string", "completed": "int", "total": "int"},
        "Progress of a model download.",
    ),
    EventSpec(
        "system.ollama_state",
        {"running": "bool"},
        "Ollama daemon up/down transition.",
    ),
]


# --------------------------------------------------------------------------- #
# JSON-RPC frame helpers
# --------------------------------------------------------------------------- #


@dataclass
class Request:
    method: str
    params: dict[str, Any] = field(default_factory=dict)
    id: int | str | None = None

    @classmethod
    def from_obj(cls, obj: dict[str, Any]) -> Request:
        return cls(
            method=str(obj.get("method", "")),
            params=obj.get("params") or {},
            id=obj.get("id"),
        )


def make_response(req_id: int | str | None, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def make_error(
    req_id: int | str | None,
    code: int,
    message: str,
    data_code: str = ERR_GENERIC,
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message, "data": {"code": data_code}},
    }


def make_notification(method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "method": method, "params": params}


def schema() -> dict[str, Any]:
    """Serializable description of the whole contract (for TS generation)."""
    return {
        "version": 1,
        "errorCodes": {
            "PARSE_ERROR": PARSE_ERROR,
            "INVALID_REQUEST": INVALID_REQUEST,
            "METHOD_NOT_FOUND": METHOD_NOT_FOUND,
            "INVALID_PARAMS": INVALID_PARAMS,
            "INTERNAL_ERROR": INTERNAL_ERROR,
        },
        "domainErrorCodes": [
            ERR_OLLAMA_UNAVAILABLE,
            ERR_OLLAMA,
            ERR_SANDBOX,
            ERR_CONFIG,
            ERR_NOT_FOUND,
            ERR_GENERIC,
        ],
        "methods": [
            {
                "name": m.name,
                "params": m.params,
                "returns": m.returns,
                "streams": m.streams,
                "description": m.description,
            }
            for m in METHODS
        ],
        "events": [
            {"name": e.name, "payload": e.payload, "description": e.description} for e in EVENTS
        ],
    }
