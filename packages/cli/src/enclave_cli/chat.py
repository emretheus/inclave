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
from enclave_core import (
    CLIError,
    EnclaveConfig,
    EnclaveError,
    FileEntry,
    OllamaUnavailableError,
    add_file,
    find_file,
    list_files,
)
from enclave_core.errors import OllamaError
from rich.console import Console

from enclave_cli import ui
from enclave_cli.context import (
    SYSTEM_PROMPT,
    AttachedFile,
    assemble_user_prompt,
    attach,
    write_run_workdir,
)
from enclave_cli.dropdetect import parse_drop
from enclave_cli.inputline import make_session, read_input

CODE_BLOCK_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


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
    if refs is None:
        return list(list_files())
    if not refs:
        return []
    return [find_file(r) for r in refs]


def _last_python_block(messages: list[dict[str, str]]) -> str | None:
    for msg in reversed(messages):
        if msg["role"] != "assistant":
            continue
        matches = CODE_BLOCK_RE.findall(msg["content"])
        if matches:
            return str(matches[-1]).strip()
    return None


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
        except EnclaveError as e:
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
    cfg: EnclaveConfig,
    console: Console,
    err_console: Console,
) -> None:
    from enclave_sandbox import SandboxPolicy, execute_python

    tmp = Path(tempfile.mkdtemp(prefix="enclave-run-"))
    try:
        write_run_workdir(tmp, attached)
        policy = SandboxPolicy(
            workdir=tmp.resolve(),
            cpu_seconds=cfg.sandbox_cpu_seconds,
            memory_mb=cfg.sandbox_memory_mb,
        )
        try:
            result = execute_python(code, policy)
        except EnclaveError as e:
            ui.error(err_console, str(e))
            return

        ui.render_sandbox_output(
            console,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            timed_out=result.timed_out,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
    config: EnclaveConfig | None = None,
) -> int:
    if not model:
        raise CLIError(
            "no model selected. set one with: enclave models use <name>, or pass --model"
        )

    cfg = config or EnclaveConfig()
    messages: list[dict[str, str]] = []
    session_files: list[FileEntry] = _resolve_initial_files(file_refs)
    current_model = [model]  # mutable holder so /model can swap mid-session

    ui.banner(console, model, len(session_files), str(Path.cwd()))
    if session_files:
        names = ", ".join(f.name for f in session_files)
        ui.info(console, f"attached: {names}")
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
            return 3
        except EnclaveError as e:
            spinner.stop()
            console.print()
            ui.error(err_console, str(e))
            messages.pop()
            continue

        if assistant_buf:
            full = "".join(assistant_buf)
            messages.append({"role": "assistant", "content": full})
            ui.render_markdown(console, full)
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
        else:
            messages.pop()


def _list_local_model_names() -> list[str]:
    """Best-effort fetch of locally installed Ollama models.

    Returns [] when Ollama isn't running so /model still prints something useful.
    """
    try:
        from enclave_ollama.api import list_models
    except ImportError:  # pragma: no cover
        return []
    try:
        return [m.name for m in list_models()]
    except EnclaveError:
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
    cfg: EnclaveConfig,
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
        except EnclaveError as e:
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

    if cmd == "run":
        code = _last_python_block(messages)
        if not code:
            ui.warn(err_console, "no python code block in the conversation yet")
            return False
        attached_files, _ = attach(session_files)
        ui.render_code_proposal(console, code)
        if not cfg.auto_run:
            file_list = ", ".join(a.entry.name for a in attached_files) or "(no files)"
            ui.info(console, f"workdir will contain: {file_list}")
            try:
                go = console.input(f"  [bold]run in sandbox?[/bold] [{ui.DIM}][y/N][/{ui.DIM}] ")
                go = go.strip().lower()
            except (EOFError, KeyboardInterrupt):
                console.print()
                ui.info(console, "cancelled")
                return False
            if go not in ("y", "yes"):
                ui.info(console, "not running")
                return False
        _execute_in_sandbox(code, attached_files, cfg, console, err_console)
        return False

    ui.warn(err_console, f"unknown command: /{cmd}  (try /help)")
    return False
