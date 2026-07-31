"""Accuracy and latency benchmarks for the InClave chat pipeline."""

from .report import Summary, render_text, summarize, to_json
from .runner import FixtureModel, Model, OllamaModel, run_task, run_tasks
from .timing import StreamTimer
from .types import SCHEMA_VERSION, Category, Check, Task, TaskResult, Timing

__all__ = [
    "SCHEMA_VERSION",
    "Category",
    "Check",
    "FixtureModel",
    "Model",
    "OllamaModel",
    "StreamTimer",
    "Summary",
    "Task",
    "TaskResult",
    "Timing",
    "render_text",
    "run_task",
    "run_tasks",
    "summarize",
    "to_json",
]
