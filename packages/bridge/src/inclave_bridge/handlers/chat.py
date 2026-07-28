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

    # Turns now run on a worker thread, so a second send can arrive while one is
    # still streaming. Reject it rather than let two turns mutate live.messages.
    if not store.mark_busy(session_id):
        emitter.chat_error(
            session_id,
            "busy",
            "a turn is already running for this session",
        )
        return {"ok": False, "reason": "busy"}

    store.clear_cancel(session_id)
    turn = engine.TurnConfig(model=live.model, cfg=cfg, session_files=live.files)

    n_turns = 0
    cancelled = False
    try:
        for ev in engine.run_turn(live.messages, text, turn, stream_fn=engine.stream_chat):
            _emit_event(emitter, session_id, ev)
            if isinstance(ev, engine.TurnDoneEvent):
                n_turns = ev.n_turns
            if store.is_cancelled(session_id):
                cancelled = True
                break
        store.autosave(live)
    finally:
        store.clear_busy(session_id)

    # Confirm the stop actually happened. The reply to `chat.cancel` only means
    # the request was received; without this the UI has no way to tell "stopped"
    # from "still streaming" and has to guess (it used to guess wrong).
    if cancelled:
        emitter.chat_cancelled(session_id)
    return {"ok": True, "n_turns": n_turns, "cancelled": cancelled}


def run_last(
    params: dict[str, Any],
    emitter: EventEmitter,
    store: SessionStore,
) -> dict[str, Any]:
    session_id = str(params["session_id"])
    cfg = load_config()
    live = store.get_or_create(session_id, cfg.default_model or "")

    if not store.mark_busy(session_id):
        emitter.chat_error(session_id, "busy", "a turn is already running for this session")
        return {"ok": False, "reason": "busy"}

    store.clear_cancel(session_id)
    turn = engine.TurnConfig(model=live.model, cfg=cfg, session_files=live.files)
    cancelled = False
    try:
        for ev in engine.run_last_block(live.messages, turn):
            _emit_event(emitter, session_id, ev)
            if store.is_cancelled(session_id):
                cancelled = True
                break
    finally:
        store.clear_busy(session_id)

    if cancelled:
        emitter.chat_cancelled(session_id)
    return {"ok": True, "cancelled": cancelled}


def cancel(
    params: dict[str, Any],
    emitter: EventEmitter,
    store: SessionStore,
) -> dict[str, Any]:
    """Request that an in-flight turn stop.

    Returns `accepted` so the caller can tell whether there was actually a turn
    running. The UI must not clear its busy state on this reply — the turn is
    still winding down at this point; wait for the `chat.cancelled` event.
    """
    session_id = str(params["session_id"])
    was_running = store.is_busy(session_id)
    store.request_cancel(session_id)
    if not was_running:
        # Nothing to stop. Clear the flag so it can't leak into the next turn.
        store.clear_cancel(session_id)
    return {"ok": True, "accepted": was_running}
