"""Chat REPL — multi-turn streaming, slash commands, workspace files, /run.

The *behavior* of a turn (streaming, auto-run, sandbox feedback) lives in
`chat_engine.py` as a headless, event-yielding loop shared with the desktop
bridge. This file is the terminal renderer: it reads input, drives the engine,
and paints events with `rich`. Visual style is in `ui.py`; drop detection in
`dropdetect.py`.
"""

from __future__ import annotations

import glob
from collections.abc import Callable, Iterator
from pathlib import Path

from inclave_core import (
    LAST,
    FileEntry,
    InClaveConfig,
    InClaveError,
    Session,
    add_file,
    find_file,
    get_logger,
    list_files,
    load_session,
    save_session,
)
from rich.console import Console

from inclave_cli import chat_engine as engine
from inclave_cli import ui
from inclave_cli.context import SYSTEM_PROMPT
from inclave_cli.dropdetect import parse_drop
from inclave_cli.inputline import make_session, read_input

log = get_logger()

# Re-exported so existing imports / tests that reach for these from chat.py keep
# working. The canonical definitions now live in chat_engine.
CODE_BLOCK_RE = engine.CODE_BLOCK_RE
MAX_AUTORUN_TURNS = engine.MAX_AUTORUN_TURNS


def _autosave(
    model: str,
    messages: list[dict[str, str]],
    session_files: list[FileEntry],
    name: str = LAST,
) -> None:
    """Persist the running conversation. Best-effort — never aborts the REPL."""
    try:
        sess = Session(
            model=model,
            workdir=str(Path.cwd()),
            file_ids=[f.id for f in session_files],
            messages=messages,
        )
        save_session(sess, name)
        log.debug(
            "autosaved session name=%s turns=%d files=%d",
            name,
            sum(1 for m in messages if m["role"] == "assistant"),
            len(session_files),
        )
    except Exception as exc:  # pragma: no cover — never crash the chat on a disk issue
        log.warning("autosave failed: %s", exc)


def _stream_chat(model: str, messages: list[dict[str, str]]) -> Iterator[str]:
    """Thin wrapper over the engine's streamer. Kept as a patchable seam: tests
    monkeypatch `inclave_cli.chat._stream_chat`, and the REPL routes the engine
    through it via `stream_fn=`.
    """
    yield from engine.stream_chat(model, messages)


def _resolve_initial_files(refs: list[str] | None) -> list[FileEntry]:
    """Resolve --file refs to FileEntry objects."""
    if not refs:
        return []
    if refs == ["all"]:
        return list(list_files())
    return [find_file(r) for r in refs]


def _attach_paths(
    paths: list[Path],
    session_files: list[FileEntry],
    console: Console,
    err_console: Console,
) -> int:
    """Add to workspace + session. Returns number newly attached."""
    n_new = 0
    for p in paths:
        try:
            entry, was_new = add_file(p)
        except InClaveError as e:
            ui.error(err_console, str(e))
            continue
        if not any(s.id == entry.id for s in session_files):
            session_files.append(entry)
            n_new += 1
        tag = "added" if was_new else "already in workspace"
        console.print(f"  [green]+[/green] {entry.name}  [dim]({tag})[/dim]")
    return n_new


def _render_event(
    event: engine.ChatEvent,
    console: Console,
    err_console: Console,
    buf: list[str],
) -> None:
    """Paint one engine event. `buf` accumulates the current message's tokens so
    we render Markdown once, after a message completes (not per-token).
    """
    if isinstance(event, engine.TokenEvent):
        buf.append(event.delta)
    elif isinstance(event, engine.MessageDoneEvent):
        ui.render_markdown(console, "".join(buf))
        console.print()
        buf.clear()
    elif isinstance(event, engine.RunStartEvent):
        pass  # the rendered code block already showed; nothing extra to print
    elif isinstance(event, engine.RunOutputEvent):
        ui.render_sandbox_output(
            console,
            stdout=event.stdout,
            stderr=event.stderr,
            exit_code=event.exit_code,
            duration_ms=event.duration_ms,
            timed_out=event.timed_out,
        )
        console.print()
    elif isinstance(event, engine.ErrorEvent):
        if event.code == "warning":
            ui.warn(err_console, event.message)
        elif event.code == "ollama_unavailable":
            ui.error(err_console, event.message)
            ui.info(
                err_console,
                "type [bold]/setup[/bold] when ollama is back, or [bold]/exit[/bold] to quit.",
            )
        else:
            ui.error(err_console, event.message)
    elif isinstance(event, engine.TurnDoneEvent):
        pass


def _make_reader(session_files: list[FileEntry], console: Console) -> Callable[[str], str]:
    """Build a `read(prompt) -> str` function."""
    import sys

    if not sys.stdin.isatty():
        return lambda _prompt: console.input(ui.PROMPT)

    def _refs() -> list[str]:
        out: list[str] = []
        for f in session_files:
            out.append(f.id)
            out.append(f.name)
        return out

    pt_session = make_session(_refs, _list_local_model_names)
    return lambda prompt_html: read_input(pt_session, prompt_html)


def run_chat(
    console: Console,
    err_console: Console,
    model: str,
    *,
    file_refs: list[str] | None = None,
    config: InClaveConfig | None = None,
    resume: bool = False,
) -> int:
    cfg = config or InClaveConfig()
    messages: list[dict[str, str]] = []
    session_files: list[FileEntry] = []
    resumed_from: str | None = None

    if resume:
        prior = load_session(LAST)
        if prior is None:
            ui.info(console, "no saved session at ~/.inclave/sessions/last.json")
        else:
            messages = list(prior.messages)
            for fid in prior.file_ids:
                try:
                    session_files.append(find_file(fid))
                except InClaveError:
                    ui.warn(err_console, f"attached file no longer in workspace: {fid}")
            if prior.model and model == (config.default_model if config else None):
                model = prior.model
            resumed_from = prior.saved_at or "unknown"
            log.debug(
                "chat: resumed model=%s turns=%d files=%d",
                model,
                sum(1 for m in messages if m["role"] == "assistant"),
                len(session_files),
            )

    if not resume or not resumed_from:
        session_files = _resolve_initial_files(file_refs)

    current_model = [model]  # mutable holder so /model can swap mid-session

    ui.banner(console, model, len(session_files), str(Path.cwd()))
    if resumed_from:
        n_turns = sum(1 for m in messages if m["role"] == "assistant")
        plural = "s" if n_turns != 1 else ""
        ui.info(console, f"resumed: {n_turns} turn{plural} · saved {resumed_from}")
    if session_files:
        names = ", ".join(f.name for f in session_files)
        ui.info(console, f"attached: {names}")
        console.print()

    import sys as _sys

    if _sys.stdin.isatty() and _sys.stdout.isatty():
        from inclave_cli.onboarding import (
            _ollama_up,
            ensure_default_model,
            ensure_ollama_running,
        )

        try:
            if not _ollama_up():
                ensure_ollama_running(console, err_console)
            if not current_model[0]:
                current_model[0] = ensure_default_model(console, err_console)
                console.print()
        except InClaveError as e:
            ui.error(err_console, str(e))
            ui.info(console, "you can retry with [bold]/setup[/bold] any time.")
            console.print()

    read = _make_reader(session_files, console)
    pending_exit = False

    while True:
        try:
            user_input = read("<ansicyan><b>›</b></ansicyan> ").strip()
        except EOFError:
            console.print()
            ui.info(console, "bye")
            return 0
        except KeyboardInterrupt:
            if pending_exit:
                console.print()
                ui.info(console, "bye")
                return 0
            console.print()
            ui.info(console, "(press Ctrl+C again to exit)")
            pending_exit = True
            continue

        pending_exit = False
        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", ":q", ":quit"):
            ui.info(console, "bye")
            return 0

        dropped = parse_drop(user_input)
        question_text: str | None = None
        if dropped:
            n = _attach_paths(dropped.paths, session_files, console, err_console)
            if dropped.question:
                question_text = dropped.question
            else:
                ui.info(
                    console,
                    f"{n} new file{'s' if n != 1 else ''} attached. ask away.",
                )
                continue
        elif user_input.startswith("/"):
            if _handle_slash(
                user_input,
                messages,
                session_files,
                current_model,
                cfg,
                console,
                err_console,
            ):
                return 0
            continue
        else:
            question_text = user_input

        if not current_model[0]:
            ui.warn(
                err_console,
                "no model set yet. run [bold]/setup[/bold] to install one, "
                "or [bold]/model <name>[/bold] if you already have one.",
            )
            continue

        # Drive the headless engine; render each event. The spinner spins until
        # the first token of each message arrives.
        turn_cfg = engine.TurnConfig(model=current_model[0], cfg=cfg, session_files=session_files)
        spinner = ui.thinking(console)
        spinner.start()
        spinner_running = True
        buf: list[str] = []
        cancelled = False
        try:
            for event in engine.run_turn(messages, question_text, turn_cfg, stream_fn=_stream_chat):
                if spinner_running and isinstance(event, (engine.TokenEvent, engine.ErrorEvent)):
                    spinner.stop()
                    spinner_running = False
                # Restart the spinner before a follow-up message streams.
                if isinstance(event, engine.RunOutputEvent):
                    _render_event(event, console, err_console, buf)
                    spinner = ui.thinking(console)
                    spinner.start()
                    spinner_running = True
                    continue
                _render_event(event, console, err_console, buf)
        except KeyboardInterrupt:
            cancelled = True
        finally:
            if spinner_running:
                spinner.stop()

        if cancelled:
            console.print()
            ui.info(console, "(stream cancelled)")
            continue

        n_turns = sum(1 for m in messages if m["role"] == "assistant")
        ui.status_hint(
            console,
            model=current_model[0],
            n_files=len(session_files),
            n_turns=n_turns,
            workdir=str(Path.cwd()),
        )
        console.print()
        _autosave(current_model[0], messages, session_files)


def _list_local_model_names() -> list[str]:
    """Best-effort fetch of locally installed Ollama models."""
    try:
        from inclave_ollama.api import list_models
    except ImportError:  # pragma: no cover
        return []
    try:
        return [m.name for m in list_models()]
    except InClaveError:
        return []


def _handle_model_switch(
    arg: str,
    current_model: list[str],
    console: Console,
    err_console: Console,
) -> None:
    if not arg:
        ui.info(console, f"current model: {current_model[0]}")
        names = _list_local_model_names()
        if not names:
            ui.info(console, "no locally installed models found (or Ollama is not running)")
            return
        console.print()
        for name in names:
            marker = "[green]●[/green]" if name == current_model[0] else f"[{ui.DIM}]·[/{ui.DIM}]"
            console.print(f"  {marker} {name}")
        console.print()
        ui.info(console, "switch with: /model <name>")
        return

    target = arg.strip()
    available = _list_local_model_names()
    if available and target not in available:
        with_tag = next((n for n in available if n == target or n.split(":", 1)[0] == target), None)
        if with_tag is None:
            ui.warn(err_console, f"model not installed: {target}")
            if available:
                console.print(f"  [{ui.DIM}]available: {', '.join(available)}[/{ui.DIM}]")
            return
        target = with_tag

    current_model[0] = target
    ui.ok(console, f"switched to {target}")


def _handle_slash(
    line: str,
    messages: list[dict[str, str]],
    session_files: list[FileEntry],
    current_model: list[str],
    cfg: InClaveConfig,
    console: Console,
    err_console: Console,
) -> bool:
    cmd, *rest = line[1:].split(maxsplit=1)
    arg = rest[0] if rest else ""
    cmd = cmd.lower()

    if cmd in ("exit", "quit", "q"):
        ui.info(console, "bye")
        return True

    if cmd == "help":
        console.print(ui.help_text())
        console.print()
        return False

    if cmd == "clear":
        messages.clear()
        ui.info(console, "history cleared")
        return False

    if cmd == "reset":
        messages.clear()
        session_files.clear()
        ui.info(console, "conversation and attached files cleared")
        return False

    if cmd == "model":
        _handle_model_switch(arg, current_model, console, err_console)
        return False

    if cmd == "setup":
        from inclave_cli.onboarding import (
            ensure_default_model,
            ensure_ollama_running,
        )

        try:
            ensure_ollama_running(console, err_console)
            chosen = ensure_default_model(console, err_console)
        except InClaveError as e:
            ui.error(err_console, str(e))
            return False
        current_model[0] = chosen
        ui.ok(console, f"ready · model: {chosen}")
        return False

    if cmd == "files":
        attached_ids = {s.id for s in session_files}
        if arg == "all":
            ui.render_files(console, list_files(), attached_ids=attached_ids, title="workspace")
        else:
            ui.render_files(console, session_files, attached_ids=attached_ids, title="attached")
        return False

    if cmd == "file":
        if not arg:
            ui.warn(err_console, "usage: /file <path>  or  /file @<id|name>")
            return False
        try:
            if arg.startswith("@"):
                entry = find_file(arg[1:])
                if not any(s.id == entry.id for s in session_files):
                    session_files.append(entry)
                ui.ok(console, f"attached {entry.name}")
                return False
            expanded = Path(arg).expanduser()
            if any(ch in arg for ch in "*?["):
                matches = sorted(Path(p) for p in glob.glob(str(expanded)) if Path(p).is_file())
                if not matches:
                    ui.warn(err_console, f"no files match: {arg}")
                    return False
                _attach_paths(matches, session_files, console, err_console)
                return False
            _attach_paths([expanded], session_files, console, err_console)
        except InClaveError as e:
            ui.error(err_console, str(e))
        return False

    if cmd == "detach":
        if not arg:
            ui.warn(err_console, "usage: /detach <id|name>")
            return False
        before = len(session_files)
        session_files[:] = [f for f in session_files if f.id != arg and f.name != arg]
        if len(session_files) == before:
            ui.warn(err_console, f"no attached file matches: {arg}")
        else:
            ui.info(console, f"detached: {arg}")
        return False

    if cmd == "save":
        name = arg.strip()
        if not name:
            ui.warn(err_console, "usage: /save <name>")
            return False
        if not any(m["role"] == "assistant" for m in messages):
            ui.warn(err_console, "nothing to save yet — no assistant turns")
            return False
        sess = Session(
            model=current_model[0],
            workdir=str(Path.cwd()),
            file_ids=[f.id for f in session_files],
            messages=messages,
        )
        try:
            save_session(sess, name)
        except InClaveError as e:
            ui.error(err_console, str(e))
            return False
        ui.ok(console, f"saved as {name}")
        return False

    if cmd == "run":
        turn_cfg = engine.TurnConfig(model=current_model[0], cfg=cfg, session_files=session_files)
        buf: list[str] = []
        for event in engine.run_last_block(messages, turn_cfg):
            _render_event(event, console, err_console, buf)
        return False

    ui.warn(err_console, f"unknown command: /{cmd}  (try /help)")
    return False


# SYSTEM_PROMPT is referenced by some callers/tests via chat; keep it importable.
__all__ = ["SYSTEM_PROMPT", "run_chat"]
