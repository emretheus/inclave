"""Core value types for the eval harness.

Kept free of any Ollama or CLI import so the scoring and reporting layers stay
testable without a model running.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

SCHEMA_VERSION = 1


class Category(StrEnum):
    """What capability a task probes.

    Used to break the summary down per-capability — an aggregate score hides
    the case where code generation regresses while plain Q&A stays flat.
    """

    CODEGEN = "codegen"
    FILE_QA = "file_qa"
    REFUSAL = "refusal"
    FORMAT = "format"


# How a task's expectation is checked. Each maps to a scorer in scoring.py.
CheckKind = Literal[
    "contains",
    "regex",
    "python_block",
    "no_python_block",
    "code_block",
    "exact",
]


@dataclass(frozen=True)
class Check:
    """A single assertion against a model reply.

    `negate` inverts the result, which is what makes refusal tasks expressible:
    "the reply must NOT contain a fabricated file path".
    """

    kind: CheckKind
    value: str = ""
    negate: bool = False
    # Human-readable reason shown in the report when this check fails.
    describe: str = ""


@dataclass(frozen=True)
class Task:
    """One benchmark case.

    `files` maps a filename to its content; the runner materialises them in a
    temp workspace so file-grounded tasks exercise the real attachment path
    rather than a mock.
    """

    id: str
    category: Category
    prompt: str
    checks: tuple[Check, ...]
    files: dict[str, str] = field(default_factory=dict)
    # Optional per-task note explaining what regression this guards against.
    rationale: str = ""


@dataclass(frozen=True)
class CheckResult:
    check: Check
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class Timing:
    """Latency breakdown for one turn, in milliseconds.

    `first_token_ms` is the number users actually feel — total duration hides a
    slow start behind fast streaming, so both are recorded separately.
    """

    first_token_ms: float | None
    total_ms: float
    token_count: int = 0

    @property
    def tokens_per_second(self) -> float | None:
        if self.total_ms <= 0 or self.token_count <= 0:
            return None
        return self.token_count / (self.total_ms / 1000.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "first_token_ms": self.first_token_ms,
            "total_ms": self.total_ms,
            "token_count": self.token_count,
            "tokens_per_second": self.tokens_per_second,
        }


@dataclass(frozen=True)
class TaskResult:
    """Outcome of running one task: did every check pass, and how slow was it."""

    task_id: str
    category: Category
    checks: tuple[CheckResult, ...]
    timing: Timing
    reply: str
    error: str | None = None

    @property
    def passed(self) -> bool:
        # An errored task is a failure regardless of checks — otherwise a task
        # that never reached the model would score as a pass on zero checks.
        if self.error is not None:
            return False
        return all(c.passed for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "category": self.category.value,
            "passed": self.passed,
            "error": self.error,
            "timing": self.timing.to_dict(),
            "checks": [
                {
                    "kind": c.check.kind,
                    "value": c.check.value,
                    "negate": c.check.negate,
                    "passed": c.passed,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
        }
