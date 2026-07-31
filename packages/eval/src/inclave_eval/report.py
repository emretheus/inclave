"""Aggregation and rendering of benchmark results."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median
from typing import Any

from .types import SCHEMA_VERSION, Category, TaskResult


def _percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile.

    Avoids a numpy dependency for a handful of samples. Nearest-rank (rather
    than interpolation) is the honest choice at small n, where an interpolated
    p95 would invent a value between two real observations.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(1, min(len(ordered), round(pct / 100.0 * len(ordered))))
    return ordered[k - 1]


@dataclass(frozen=True)
class CategoryStats:
    category: Category
    total: int
    passed: int

    @property
    def pass_rate(self) -> float:
        return 0.0 if self.total == 0 else self.passed / self.total


@dataclass(frozen=True)
class Summary:
    """Headline numbers for one benchmark run."""

    model: str
    live: bool
    total: int
    passed: int
    categories: tuple[CategoryStats, ...]
    median_first_token_ms: float | None
    p95_first_token_ms: float | None
    median_total_ms: float
    errors: int

    @property
    def pass_rate(self) -> float:
        return 0.0 if self.total == 0 else self.passed / self.total

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "model": self.model,
            "live": self.live,
            "total": self.total,
            "passed": self.passed,
            "pass_rate": self.pass_rate,
            "errors": self.errors,
            "latency": {
                "median_first_token_ms": self.median_first_token_ms,
                "p95_first_token_ms": self.p95_first_token_ms,
                "median_total_ms": self.median_total_ms,
            },
            "categories": [
                {
                    "category": c.category.value,
                    "total": c.total,
                    "passed": c.passed,
                    "pass_rate": c.pass_rate,
                }
                for c in self.categories
            ],
        }


def summarize(results: Sequence[TaskResult], model: str, live: bool) -> Summary:
    by_cat: dict[Category, list[TaskResult]] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    cats = tuple(
        CategoryStats(
            category=cat,
            total=len(rs),
            passed=sum(1 for r in rs if r.passed),
        )
        # Sorted by value for a stable report ordering across runs.
        for cat, rs in sorted(by_cat.items(), key=lambda kv: kv[0].value)
    )

    # Only successful turns contribute latency: a task that errored out early
    # would otherwise drag the median down and read as a speed improvement.
    ok = [r for r in results if r.error is None]
    first_tokens = [r.timing.first_token_ms for r in ok if r.timing.first_token_ms is not None]
    totals = [r.timing.total_ms for r in ok]

    return Summary(
        model=model,
        live=live,
        total=len(results),
        passed=sum(1 for r in results if r.passed),
        categories=cats,
        median_first_token_ms=median(first_tokens) if first_tokens else None,
        p95_first_token_ms=_percentile(first_tokens, 95) if first_tokens else None,
        median_total_ms=median(totals) if totals else 0.0,
        errors=sum(1 for r in results if r.error is not None),
    )


def to_json(summary: Summary, results: Sequence[TaskResult]) -> dict[str, Any]:
    return {
        "summary": summary.to_dict(),
        "results": [r.to_dict() for r in results],
    }


def _fmt_ms(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.0f}ms"


def render_text(summary: Summary, results: Sequence[TaskResult]) -> str:
    """Human-readable report for the terminal."""
    mode = "live" if summary.live else "fixture"
    lines = [
        f"InClave eval — {summary.model} ({mode})",
        "",
        f"  pass rate   {summary.passed}/{summary.total} ({summary.pass_rate * 100:.0f}%)",
    ]
    if summary.errors:
        lines.append(f"  errors      {summary.errors}")

    # Latency is meaningless for fixture replays (it measures string slicing),
    # so it is only reported for live runs.
    if summary.live:
        lines += [
            "",
            "  latency",
            f"    first token   median {_fmt_ms(summary.median_first_token_ms)}"
            f"  p95 {_fmt_ms(summary.p95_first_token_ms)}",
            f"    total         median {_fmt_ms(summary.median_total_ms)}",
        ]

    lines += ["", "  by category"]
    for c in summary.categories:
        lines.append(f"    {c.category.value:<12} {c.passed}/{c.total} ({c.pass_rate * 100:.0f}%)")

    failures = [r for r in results if not r.passed]
    if failures:
        lines += ["", "  failures"]
        for r in failures:
            reason = r.error or "; ".join(c.detail for c in r.checks if not c.passed and c.detail)
            lines.append(f"    {r.task_id:<24} {reason or 'check failed'}")

    return "\n".join(lines)
