"""chat.* handlers — drive the shared chat_engine, translate its events into
bridge notifications.
"""

from __future__ import annotations

from typing import Any

from inclave_cli import chat_engine as engine
from inclave_core import find_file, load_config

from inclave_bridge.events import EventEmitter
from inclave_bridge.store import SessionStore


def _resolve_files(file_ids: list[str]) -> list[Any]:
    files = []
    for fid in file_ids:
        try:
            files.append(find_file(fid))
        except Exception:
            continue
    return files


def _emit_event(emitter: EventEmitter, session_id: str, ev: engine.ChatEvent) -> None:
    if isinstance(ev, engine.TokenEvent):
        emitter.chat_token(session_id, ev.delta)
    elif isinstance(ev, engine.MessageDoneEvent):
        emitter.chat_message_done(session_id, ev.role, ev.content)
    elif isinstance(ev, engine.RunStartEvent):
        emitter.chat_run_start(session_id, ev.code)
    elif isinstance(ev, engine.RunOutputEvent):
        emitter.chat_run_output(
            session_id,
            stdout=ev.stdout,
            stderr=ev.stderr,
            exit_code=ev.exit_code,
            duration_ms=ev.duration_ms,
            timed_out=ev.timed_out,
        )
    elif isinstance(ev, engine.ErrorEvent):
        emitter.chat_error(session_id, ev.code, ev.message)
    elif isinstance(ev, engine.TurnDoneEvent):
        emitter.chat_turn_done(session_id, ev.n_turns)


def send(
    params: dict[str, Any],
    emitter: EventEmitter,
    store: SessionStore,
) -> dict[str, Any]:
    session_id = str(params["session_id"])
    text = str(params["text"])
    file_ids = list(params.get("file_ids", []))

    cfg = load_config()
    model = cfg.default_model or ""

    live = store.get_or_create(session_id, model)
    if file_ids:
        live.files = _resolve_files(file_ids)

    if not live.model:
        emitter.chat_error(
            session_id,
            "no_model",
            "no model set yet — install one in Settings or run setup",
        )
        return {"ok": False, "reason": "no_model"}

    store.clear_cancel(session_id)
    turn = engine.TurnConfig(model=live.model, cfg=cfg, session_files=live.files)

    n_turns = 0
    for ev in engine.run_turn(live.messages, text, turn, stream_fn=engine.stream_chat):
        _emit_event(emitter, session_id, ev)
        if isinstance(ev, engine.TurnDoneEvent):
            n_turns = ev.n_turns
        if store.is_cancelled(session_id):
            break

    store.autosave(live)
    return {"ok": True, "n_turns": n_turns}


def run_last(
    params: dict[str, Any],
    emitter: EventEmitter,
    store: SessionStore,
) -> dict[str, Any]:
    session_id = str(params["session_id"])
    cfg = load_config()
    live = store.get_or_create(session_id, cfg.default_model or "")
    turn = engine.TurnConfig(model=live.model, cfg=cfg, session_files=live.files)
    for ev in engine.run_last_block(live.messages, turn):
        _emit_event(emitter, session_id, ev)
    return {"ok": True}


def cancel(
    params: dict[str, Any],
    emitter: EventEmitter,
    store: SessionStore,
) -> dict[str, Any]:
    session_id = str(params["session_id"])
    store.request_cancel(session_id)
    return {"ok": True}
