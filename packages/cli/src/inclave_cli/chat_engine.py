"""Headless chat orchestration — the engine behind the REPL and the desktop app.

This module owns the *behavior* of a chat turn with no reference to a terminal,
`rich.Console`, or prompt_toolkit. It yields typed events so any front-end (the
CLI in `chat.py`, the desktop bridge in `inclave_bridge`) can render them.

The orchestration mirrors what `chat.py` did inline before the extraction:

  1. Stream the assistant reply token by token.
  2. If the reply contains a python fenced block, run it in the sandbox.
  3. Feed the sandbox observation back as a synthetic user turn.
  4. Let the model write a grounded, plain-language summary.
  5. Repeat up to MAX_AUTORUN_TURNS times.

`chat.py` (the CLI) is now a thin renderer over these events; this is the same
loop, so the existing `test_chat.py` suite continues to exercise it.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import httpx
import ollama
from inclave_core import (
    FileEntry,
    InClaveConfig,
    InClaveError,
    OllamaUnavailableError,
)
from inclave_core.errors import OllamaError

from inclave_cli.context import (
    SYSTEM_PROMPT,
    AttachedFile,
    assemble_user_prompt,
    attach,
    write_run_workdir,
)

# Match fenced code blocks. We accept three flavors:
#   1. ```python\n…\n```   — the canonical form (also: py, py3, python3)
#   2. ```\n…\n```          — language-tagless fence (small models do this)
#   3. <indented Python> — *not* matched here; only fenced code auto-runs.
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
# the comment, we'd run that too, and so on. Three rounds is generous.
MAX_AUTORUN_TURNS = 3

_PY_LANGS = {"", "python", "py", "py3", "python3"}


# --------------------------------------------------------------------------- #
# Events
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TokenEvent:
    """One streamed chunk of an assistant message."""

    kind: Literal["token"] = "token"
    delta: str = ""


@dataclass(frozen=True)
class MessageDoneEvent:
    """An assistant message has finished streaming and was committed."""

    role: str = "assistant"
    content: str = ""
    kind: Literal["message_done"] = "message_done"


@dataclass(frozen=True)
class RunStartEvent:
    """A python block from the latest reply is about to run in the sandbox."""

    code: str = ""
    kind: Literal["run_start"] = "run_start"


@dataclass(frozen=True)
class RunOutputEvent:
    """The sandbox finished running a block."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0
    timed_out: bool = False
    kind: Literal["run_output"] = "run_output"


@dataclass(frozen=True)
class ErrorEvent:
    """A recoverable error during the turn (Ollama down, sandbox error…)."""

    message: str = ""
    code: str = "error"
    kind: Literal["error"] = "error"


@dataclass(frozen=True)
class TurnDoneEvent:
    """The whole turn (including any auto-run rounds) is complete."""

    n_turns: int = 0
    kind: Literal["turn_done"] = "turn_done"


ChatEvent = (
    TokenEvent | MessageDoneEvent | RunStartEvent | RunOutputEvent | ErrorEvent | TurnDoneEvent
)


# --------------------------------------------------------------------------- #
# Code-block detection (unchanged logic, lifted from chat.py)
# --------------------------------------------------------------------------- #


def python_blocks_in(content: str) -> list[str]:
    """Return every python-ish fenced code block in `content`."""
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


def last_python_block(messages: list[dict[str, str]]) -> str | None:
    """Most recent python block across all assistant turns (for /run)."""
    for msg in reversed(messages):
        if msg["role"] != "assistant":
            continue
        blocks = python_blocks_in(msg["content"])
        if blocks:
            return blocks[-1]
    return None


def python_block_in_latest_assistant(messages: list[dict[str, str]]) -> str | None:
    """Python block from THIS turn's assistant reply only — does not walk history."""
    if not messages or messages[-1]["role"] != "assistant":
        return None
    blocks = python_blocks_in(messages[-1]["content"])
    return blocks[-1] if blocks else None


# --------------------------------------------------------------------------- #
# Streaming + sandbox
# --------------------------------------------------------------------------- #


def stream_chat(model: str, messages: list[dict[str, str]]) -> Iterator[str]:
    """Yield content chunks from ollama.chat. Raises InClaveError subclasses."""
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


@dataclass(frozen=True)
class _SandboxOutcome:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    timed_out: bool


def run_in_sandbox(
    code: str,
    attached: list[AttachedFile],
    cfg: InClaveConfig,
) -> _SandboxOutcome | None:
    """Run code in the sandbox. Returns the outcome, or None if the sandbox
    itself errored (e.g. sandbox-exec missing). Pure — no rendering.
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
        result = execute_python(code, policy)
        return _SandboxOutcome(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            timed_out=result.timed_out,
        )
    except InClaveError:
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def format_sandbox_observation(outcome: _SandboxOutcome) -> str:
    """Turn a sandbox outcome into a short text block fed back into the
    conversation as if the user said it.
    """
    stdout = outcome.stdout or ""
    stderr = outcome.stderr or ""

    MAX = 4_000
    if len(stdout) > MAX:
        stdout = stdout[:MAX] + "\n[... output truncated ...]"
    if len(stderr) > MAX:
        stderr = stderr[:MAX] + "\n[... stderr truncated ...]"

    pieces = ["[sandbox executed your last code block]"]
    if outcome.timed_out:
        pieces.append("status: TIMED OUT")
    else:
        pieces.append(f"status: exit {outcome.exit_code}")
    if stdout.strip():
        pieces.append(f"stdout:\n{stdout.rstrip()}")
    if stderr.strip():
        pieces.append(f"stderr:\n{stderr.rstrip()}")
    pieces.append(
        "Give the user a one- or two-sentence answer based on this output. "
        "Do not produce another python block unless the user asks for one."
    )
    return "\n\n".join(pieces)


# --------------------------------------------------------------------------- #
# The turn loop
# --------------------------------------------------------------------------- #


# A stream function: (model, messages) -> Iterator[str]. Injectable so the CLI
# can route through its own patchable `_stream_chat` (tests) and the bridge can
# pass `stream_chat` directly.
StreamFn = Callable[[str, list[dict[str, str]]], Iterator[str]]


@dataclass
class TurnConfig:
    model: str
    cfg: InClaveConfig
    session_files: list[FileEntry] = field(default_factory=list)


def run_turn(
    messages: list[dict[str, str]],
    question_text: str | None,
    turn: TurnConfig,
    stream_fn: StreamFn | None = None,
) -> Iterator[ChatEvent]:
    """Run one full user turn, yielding events.

    `messages` is mutated in place (the canonical conversation history) exactly
    as the CLI did before, so callers can autosave it afterwards. The system
    prompt is inserted on the first turn. `question_text` may be None when the
    caller has already appended the user message (rare); normally pass the raw
    user text and let this append it with files attached.
    """
    _stream = stream_fn or stream_chat
    attached_files, warnings = attach(turn.session_files)
    for w in warnings:
        yield ErrorEvent(message=w, code="warning")

    if not messages:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})

    if question_text is not None:
        prompt = (
            assemble_user_prompt(question_text, attached_files) if attached_files else question_text
        )
        messages.append({"role": "user", "content": prompt})

    # First assistant reply.
    try:
        buf: list[str] = []
        for piece in _stream(turn.model, messages):
            buf.append(piece)
            yield TokenEvent(delta=piece)
    except (OllamaUnavailableError, OllamaError) as e:
        messages.pop()  # drop the user message; don't poison history
        yield ErrorEvent(message=str(e), code=_error_code(e))
        return

    if not buf:
        messages.pop()
        yield TurnDoneEvent(n_turns=_count_turns(messages))
        return

    full = "".join(buf)
    messages.append({"role": "assistant", "content": full})
    yield MessageDoneEvent(role="assistant", content=full)

    # Auto-run loop.
    for _ in range(MAX_AUTORUN_TURNS):
        code = python_block_in_latest_assistant(messages)
        if not code:
            break

        attached_files, _w = attach(turn.session_files)
        yield RunStartEvent(code=code)
        outcome = run_in_sandbox(code, attached_files, turn.cfg)
        if outcome is None:
            yield ErrorEvent(message="sandbox execution failed", code="sandbox_error")
            break

        yield RunOutputEvent(
            stdout=outcome.stdout,
            stderr=outcome.stderr,
            exit_code=outcome.exit_code,
            duration_ms=outcome.duration_ms,
            timed_out=outcome.timed_out,
        )

        observation = format_sandbox_observation(outcome)
        messages.append({"role": "user", "content": observation})

        try:
            followup_buf: list[str] = []
            for piece in _stream(turn.model, messages):
                followup_buf.append(piece)
                yield TokenEvent(delta=piece)
        except (OllamaUnavailableError, OllamaError) as e:
            messages.pop()  # drop the observation
            yield ErrorEvent(message=str(e), code=_error_code(e))
            break

        if not followup_buf:
            messages.pop()
            break
        followup = "".join(followup_buf)
        messages.append({"role": "assistant", "content": followup})
        yield MessageDoneEvent(role="assistant", content=followup)

    yield TurnDoneEvent(n_turns=_count_turns(messages))


def run_last_block(
    messages: list[dict[str, str]],
    turn: TurnConfig,
) -> Iterator[ChatEvent]:
    """The /run escape hatch: re-run the most recent python block in history."""
    code = last_python_block(messages)
    if not code:
        yield ErrorEvent(message="no python code block in the conversation yet", code="no_code")
        return
    attached_files, _ = attach(turn.session_files)
    yield RunStartEvent(code=code)
    outcome = run_in_sandbox(code, attached_files, turn.cfg)
    if outcome is None:
        yield ErrorEvent(message="sandbox execution failed", code="sandbox_error")
        return
    yield RunOutputEvent(
        stdout=outcome.stdout,
        stderr=outcome.stderr,
        exit_code=outcome.exit_code,
        duration_ms=outcome.duration_ms,
        timed_out=outcome.timed_out,
    )


def _count_turns(messages: list[dict[str, str]]) -> int:
    return sum(1 for m in messages if m["role"] == "assistant")


def _error_code(e: InClaveError) -> str:
    if isinstance(e, OllamaUnavailableError):
        return "ollama_unavailable"
    if isinstance(e, OllamaError):
        return "ollama_error"
    return "error"
