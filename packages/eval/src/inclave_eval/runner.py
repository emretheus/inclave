"""Task execution.

Two model backends share one code path so fixture and live runs score through
identical logic:

* `FixtureModel`  — replays canned replies. Deterministic, no Ollama, CI-safe.
* `OllamaModel`   — streams from a real local model. Real accuracy and latency.

Only the backend differs; scoring, timing, and reporting are the same for both.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Protocol

from .scoring import run_checks
from .timing import StreamTimer
from .types import Task, TaskResult, Timing


class Model(Protocol):
    """Anything that can turn a prompt into a stream of reply chunks."""

    def stream(self, task: Task) -> Iterator[str]: ...


class FixtureModel:
    """Replays a recorded reply per task id.

    A missing fixture raises rather than returning an empty string: silently
    scoring an unrecorded task as a fail would misreport a harness gap as a
    model regression.
    """

    def __init__(self, replies: dict[str, str]) -> None:
        self._replies = replies

    def stream(self, task: Task) -> Iterator[str]:
        if task.id not in self._replies:
            raise KeyError(f"no fixture reply recorded for task {task.id!r}")
        reply = self._replies[task.id]
        # Chunked to exercise the streaming path rather than yielding one blob.
        for i in range(0, len(reply), 24):
            yield reply[i : i + 24]


class OllamaModel:
    """Streams from a real local model via the product's own chat engine."""

    def __init__(self, model: str, num_ctx: int | None = None) -> None:
        self.model = model
        self.num_ctx = num_ctx

    def stream(self, task: Task) -> Iterator[str]:
        # Imported lazily so fixture-only runs never require the ollama client.
        from inclave_cli.chat_engine import stream_chat

        messages = _build_messages(task)
        return stream_chat(self.model, messages, num_ctx=self.num_ctx)


def _build_messages(task: Task) -> list[dict[str, str]]:
    """Compose the prompt, inlining any attached files as fenced blocks."""
    parts: list[str] = []
    for name, content in task.files.items():
        parts.append(f"--- {name} ---\n{content}")
    parts.append(task.prompt)
    return [{"role": "user", "content": "\n\n".join(parts)}]


def run_task(task: Task, model: Model) -> TaskResult:
    """Run one task, scoring and timing it.

    Model errors are captured into the result rather than raised, so one broken
    task cannot abort a whole benchmark run.
    """
    timer = StreamTimer()
    chunks: list[str] = []
    error: str | None = None
    try:
        for piece in timer.wrap(model.stream(task)):
            chunks.append(piece)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    reply = "".join(chunks)
    timing = timer.result()
    # Checks still run on a partial reply: a truncated answer that happens to
    # satisfy them is useful signal, and `error` already forces `passed` False.
    checks = run_checks(task.checks, reply)
    return TaskResult(
        task_id=task.id,
        category=task.category,
        checks=checks,
        timing=timing,
        reply=reply,
        error=error,
    )


def run_tasks(tasks: Iterable[Task], model: Model) -> list[TaskResult]:
    return [run_task(t, model) for t in tasks]


__all__ = [
    "FixtureModel",
    "Model",
    "OllamaModel",
    "Timing",
    "run_task",
    "run_tasks",
]
