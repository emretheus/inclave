from __future__ import annotations

from inclave_eval.report import _percentile, render_text, summarize, to_json
from inclave_eval.runner import FixtureModel, run_tasks
from inclave_eval.tasks import DEFAULT_TASKS, GOOD_REPLIES, REGRESSED_REPLIES
from inclave_eval.types import Category, Check, CheckResult, TaskResult, Timing


def _result(
    tid: str, passed: bool, first: float | None, total: float, error: str | None = None
) -> TaskResult:
    check = Check(kind="contains", value="x")
    return TaskResult(
        task_id=tid,
        category=Category.CODEGEN,
        checks=(CheckResult(check=check, passed=passed),),
        timing=Timing(first_token_ms=first, total_ms=total, token_count=3),
        reply="",
        error=error,
    )


def test_pass_rate_and_totals() -> None:
    s = summarize([_result("a", True, 10, 100), _result("b", False, 20, 200)], "m", live=True)
    assert (s.total, s.passed) == (2, 1)
    assert s.pass_rate == 0.5


def test_empty_run_does_not_divide_by_zero() -> None:
    s = summarize([], "m", live=False)
    assert s.pass_rate == 0.0
    assert s.median_first_token_ms is None


def test_errored_tasks_excluded_from_latency() -> None:
    """An early crash must not read as a latency improvement."""
    results = [
        _result("ok", True, 100, 1000),
        _result("bad", False, 1, 2, error="boom"),
    ]
    s = summarize(results, "m", live=True)
    assert s.errors == 1
    # Only the successful turn contributes.
    assert s.median_first_token_ms == 100
    assert s.median_total_ms == 1000


def test_category_breakdown_is_sorted_and_counted() -> None:
    results = list(run_tasks(DEFAULT_TASKS, FixtureModel(GOOD_REPLIES)))
    s = summarize(results, "fixtures", live=False)
    names = [c.category.value for c in s.categories]
    assert names == sorted(names)
    assert sum(c.total for c in s.categories) == len(DEFAULT_TASKS)
    assert all(c.pass_rate == 1.0 for c in s.categories)


def test_percentile_nearest_rank() -> None:
    assert _percentile([1, 2, 3, 4, 5], 95) == 5
    assert _percentile([10], 95) == 10
    assert _percentile([], 95) == 0.0


def test_render_hides_latency_for_fixture_runs() -> None:
    """Fixture timings measure string slicing, not the model — don't report them."""
    results = run_tasks(DEFAULT_TASKS, FixtureModel(GOOD_REPLIES))
    text = render_text(summarize(results, "fixtures", live=False), results)
    assert "latency" not in text
    assert "pass rate" in text


def test_render_shows_latency_and_failures_for_live_runs() -> None:
    results = run_tasks(DEFAULT_TASKS, FixtureModel(REGRESSED_REPLIES))
    text = render_text(summarize(results, "llama3.2:3b", live=True), results)
    assert "latency" in text
    assert "failures" in text
    assert "refusal-no-invented-file" in text


def test_json_payload_is_serializable_and_versioned() -> None:
    import json

    results = run_tasks(DEFAULT_TASKS, FixtureModel(GOOD_REPLIES))
    payload = to_json(summarize(results, "fixtures", live=False), results)
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped["summary"]["schema_version"] == 1
    assert len(round_tripped["results"]) == len(DEFAULT_TASKS)
