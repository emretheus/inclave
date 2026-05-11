"""Chat REPL — multi-turn streaming, slash commands, workspace files, /run.

Visual style is split into `ui.py` so this file stays about behavior.
Drag-and-drop file detection lives in `dropdetect.py`.
"""

from __future__ import annotations

import glob
import re
import shutil
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import ollama
from inclave_core import (
    LAST,
    FileEntry,
    InClaveConfig,
    InClaveError,
    OllamaUnavailableError,
    Session,
    add_file,
    find_file,
    get_logger,
    list_files,
    load_session,
    save_session,
)
from inclave_core.errors import OllamaError
from rich.console import Console

from inclave_cli import ui
from inclave_cli.context import (
    SYSTEM_PROMPT,
    AttachedFile,
    assemble_user_prompt,
    attach,
    write_run_workdir,
)
from inclave_cli.dropdetect import parse_drop
from inclave_cli.inputline import make_session, read_input

log = get_logger()

# Match fenced code blocks. We accept three flavors:
#   1. ```python\n…\n```   — the canonical form (also: py, py3, python3)
#   2. ```\n…\n```          — language-tagless fence (small models do this)
#   3. <indented Python> — *not* matched here; only fenced code auto-runs.
# The "imports + def/print on a top-level line" heuristic gives us a cheap
# way to skip ```bash``` or other non-python fences while still catching
# language-tagless python blocks.
CODE_BLOCK_RE = re.compile(
    r"```(?P<lang>[\w.+-]*)\s*\n(?P<body>.*?)```",
    re.DOTALL,
)
_PY_HINT_RE = re.compile(
    r"^\s*(?:import\s|from\s+\S+\s+import\s|def\s|class\s|print\s*\(|"
    r"\w+\s*=\s|if\s+__name__\s*==)",
    re.MULTILINE,
)

# Hard ceiling on auto-run iterations within a single user turn. The model
# writes code → we run it → model comments. If the model writes more code in
# the comment, we'd run that too, and so on. Three rounds is generous; in
# practice the second is usually a plain-language summary.
MAX_AUTORUN_TURNS = 3


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
    try:
        response = ollama.chat(model=model, messages=messages, stream=True)
        for chunk in response:
            msg = chunk.get("message") or {}
            piece = msg.get("content")
            if piece:
                yield piece
    except (httpx.ConnectError, ConnectionError) as e:
        raise OllamaUnavailableError("Ollama is not running. Start it with: ollama serve") from e
    except ollama.ResponseError as e:
        raise OllamaError(f"Ollama error: {e.error}") from e


def _resolve_initial_files(refs: list[str] | None) -> list[FileEntry]:
    """Resolve --file refs to FileEntry objects.

    None / empty → start with an empty session. The workspace can contain
    leftover files from earlier sessions; attaching them all by default
    would silently inject unwanted context into the next chat. Users who
    want everything pass `--file all` or use `/files all` once inside.
    """
    if not refs:
        return []
    if refs == ["all"]:
        return list(list_files())
    return [find_file(r) for r in refs]


_PY_LANGS = {"", "python", "py", "py3", "python3"}


def _python_blocks_in(content: str) -> list[str]:
    """Return every python-ish fenced code block in `content`.

    Accepts ``` (no language tag) and ```py / ```python (any case). Tagless
    fences must also look like python (import / def / print / assignment)
    so we don't accidentally execute a shell session paste.
    """
    out: list[str] = []
    for m in CODE_BLOCK_RE.finditer(content):
        lang = m.group("lang").lower()
        body = m.group("body")
        if lang not in _PY_LANGS:
            continue
        if not lang and not _PY_HINT_RE.search(body):
            continue
        out.append(body.strip())
    return out


def _last_python_block(messages: list[dict[str, str]]) -> str | None:
    """Most recent python block across all assistant turns. Used by the
    `/run` slash command, which is explicitly a "rerun the last code"
    escape hatch and should reach back through history.
    """
    for msg in reversed(messages):
        if msg["role"] != "assistant":
            continue
        blocks = _python_blocks_in(msg["content"])
        if blocks:
            return blocks[-1]
    return None


def _python_block_in_latest_assistant(messages: list[dict[str, str]]) -> str | None:
    """Python block from THIS turn's assistant reply only — does not walk
    history. Used by the auto-run loop so a follow-up reply that contains
    no code doesn't re-execute a stale block from an earlier turn.
    """
    if not messages or messages[-1]["role"] != "assistant":
        return None
    blocks = _python_blocks_in(messages[-1]["content"])
    return blocks[-1] if blocks else None


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


def _execute_in_sandbox(
    code: str,
    attached: list[AttachedFile],
    cfg: InClaveConfig,
    console: Console,
    err_console: Console,
) -> object | None:
    """Run code in the sandbox and render its output. Returns the
    ExecutionResult so callers can feed stdout back to the model. Returns
    None if the sandbox itself errored.
    """
    from inclave_sandbox import SandboxPolicy, execute_python

    tmp = Path(tempfile.mkdtemp(prefix="inclave-run-"))
    try:
        write_run_workdir(tmp, attached)
        policy = SandboxPolicy(
            workdir=tmp.resolve(),
            cpu_seconds=cfg.sandbox_cpu_seconds,
            memory_mb=cfg.sandbox_memory_mb,
        )
        try:
            result = execute_python(code, policy)
        except InClaveError as e:
            ui.error(err_console, str(e))
            return None

        ui.render_sandbox_output(
            console,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            timed_out=result.timed_out,
        )
        return result
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _format_sandbox_observation(result: object) -> str:
    """Turn a sandbox ExecutionResult into a short text block to feed back
    into the conversation as if the user said it. The model uses this to
    write a human-language summary of what just ran.
    """
    # Access by attribute (duck-typed against ExecutionResult).
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    exit_code = getattr(result, "exit_code", 0)
    timed_out = getattr(result, "timed_out", False)

    # Cap to keep us well under context limits even on big tracebacks.
    MAX = 4_000
    if len(stdout) > MAX:
        stdout = stdout[:MAX] + "\n[... output truncated ...]"
    if len(stderr) > MAX:
        stderr = stderr[:MAX] + "\n[... stderr truncated ...]"

    pieces = ["[sandbox executed your last code block]"]
    if timed_out:
        pieces.append("status: TIMED OUT")
    else:
        pieces.append(f"status: exit {exit_code}")
    if stdout.strip():
        pieces.append(f"stdout:\n{stdout.rstrip()}")
    if stderr.strip():
        pieces.append(f"stderr:\n{stderr.rstrip()}")
    pieces.append(
        "Give the user a one- or two-sentence answer based on this output. "
        "Do not produce another python block unless the user asks for one."
    )
    return "\n\n".join(pieces)


def _make_reader(session_files: list[FileEntry], console: Console) -> Callable[[str], str]:
    """Build a `read(prompt) -> str` function.

    When stdin is a TTY → use prompt_toolkit (slash autocomplete + history).
    Otherwise (tests, pipes) → fall back to Rich's console.input so existing
    `monkeypatch(Console.input)` tests keep working.
    """
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
    # Empty model is allowed — the REPL still opens; the banner shows the
    # missing-model state and the user can type `/setup` to fix it.
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
            # Re-resolve attached file ids; drop any that were removed since.
            for fid in prior.file_ids:
                try:
                    session_files.append(find_file(fid))
                except InClaveError:
                    ui.warn(err_console, f"attached file no longer in workspace: {fid}")
            # Override the model from saved session only if caller didn't pass --model.
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
        # Fresh session — apply --file refs (None == all workspace files).
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

    # If prerequisites are missing, walk the user through setup right now —
    # interactive only. Non-TTY (CliRunner, pipes) skips and lets the REPL
    # surface inline warnings on first message instead.
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
            # Don't kill the REPL — surface the error and let the user retry
            # via /setup or just chat (which will warn again on first send).
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

        # Bare-word exits — accept the obvious words without requiring `/`.
        if user_input.lower() in ("exit", "quit", ":q", ":quit"):
            ui.info(console, "bye")
            return 0

        # Drag-and-drop wins over slash detection so absolute paths like
        # "/Users/foo/bar.pdf" are recognized as dropped files, not commands.
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

        # Need a model before we can stream. Guide the user instead of crashing.
        if not current_model[0]:
            ui.warn(
                err_console,
                "no model set yet. run [bold]/setup[/bold] to install one, "
                "or [bold]/model <name>[/bold] if you already have one.",
            )
            continue

        # Build the prompt with files attached and system prompt
        attached_files, warnings = attach(session_files)
        for w in warnings:
            ui.warn(err_console, w)

        if not messages:
            messages.append({"role": "system", "content": SYSTEM_PROMPT})
        prompt = (
            assemble_user_prompt(question_text, attached_files) if attached_files else question_text
        )
        messages.append({"role": "user", "content": prompt})

        # Spinner spins while tokens stream into a buffer. We render the full
        # turn as Markdown only once, after streaming completes — that avoids
        # the "raw text then re-rendered" double-print issue.
        spinner = ui.thinking(console)
        spinner.start()
        assistant_buf: list[str] = []
        try:
            for piece in _stream_chat(current_model[0], messages):
                assistant_buf.append(piece)
            spinner.stop()
        except KeyboardInterrupt:
            spinner.stop()
            console.print()
            ui.info(console, "(stream cancelled)")
            messages.pop()
            continue
        except OllamaUnavailableError as e:
            spinner.stop()
            console.print()
            ui.error(err_console, str(e))
            ui.info(
                err_console,
                "type [bold]/setup[/bold] when ollama is back, or [bold]/exit[/bold] to quit.",
            )
            messages.pop()  # drop the user message; don't poison history
            continue
        except InClaveError as e:
            spinner.stop()
            console.print()
            ui.error(err_console, str(e))
            messages.pop()
            continue

        if not assistant_buf:
            messages.pop()
            continue

        full = "".join(assistant_buf)
        messages.append({"role": "assistant", "content": full})
        ui.render_markdown(console, full)
        console.print()

        # Auto-run loop: only fires on python in *this turn's* assistant
        # reply. The follow-up message (sandbox observation → model
        # summary) ordinarily has no code, which ends the loop. Capped at
        # MAX_AUTORUN_TURNS in case a confused model keeps emitting code.
        for _ in range(MAX_AUTORUN_TURNS):
            code = _python_block_in_latest_assistant(messages)
            if not code:
                break

            attached_files, _w = attach(session_files)
            result = _execute_in_sandbox(code, attached_files, cfg, console, err_console)
            if result is None:
                break  # sandbox itself errored; UI already showed it
            console.print()

            observation = _format_sandbox_observation(result)
            messages.append({"role": "user", "content": observation})

            spinner = ui.thinking(console)
            spinner.start()
            followup_buf: list[str] = []
            try:
                for piece in _stream_chat(current_model[0], messages):
                    followup_buf.append(piece)
                spinner.stop()
            except KeyboardInterrupt:
                spinner.stop()
                console.print()
                ui.info(console, "(stream cancelled)")
                messages.pop()  # drop the observation; nothing to comment on
                break
            except OllamaUnavailableError as e:
                spinner.stop()
                console.print()
                ui.error(err_console, str(e))
                messages.pop()
                break
            except InClaveError as e:
                spinner.stop()
                console.print()
                ui.error(err_console, str(e))
                messages.pop()
                break

            if not followup_buf:
                messages.pop()
                break
            followup = "".join(followup_buf)
            messages.append({"role": "assistant", "content": followup})
            ui.render_markdown(console, followup)
            console.print()

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
    """Best-effort fetch of locally installed Ollama models.

    Returns [] when Ollama isn't running so /model still prints something useful.
    """
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
        # No argument → show current + list available local models.
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
        # Try a forgiving match — bare name without :tag.
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
            # Path or glob — expand and attach all
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
        # The last python block was already auto-run when the model produced
        # it. /run is the manual escape hatch — it re-executes the same code,
        # useful when the file workspace has changed since the last turn.
        code = _last_python_block(messages)
        if not code:
            ui.warn(err_console, "no python code block in the conversation yet")
            return False
        attached_files, _ = attach(session_files)
        _execute_in_sandbox(code, attached_files, cfg, console, err_console)
        return False

    ui.warn(err_console, f"unknown command: /{cmd}  (try /help)")
    return False
