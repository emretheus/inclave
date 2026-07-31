from __future__ import annotations

from collections.abc import Iterator

import pytest
from inclave_eval.runner import FixtureModel, run_task, run_tasks
from inclave_eval.tasks import DEFAULT_TASKS, GOOD_REPLIES, REGRESSED_REPLIES
from inclave_eval.types import Category, Check, Task


def test_good_fixtures_pass_every_task() -> None:
    results = run_tasks(DEFAULT_TASKS, FixtureModel(GOOD_REPLIES))
    failed = [
        (r.task_id, [c.detail for c in r.checks if not c.passed]) for r in results if not r.passed
    ]
    assert failed == [], f"well-behaved fixtures should pass: {failed}"


def test_regressed_fixtures_are_caught() -> None:
    """The harness must actually detect bad output, not just score happy paths."""
    results = run_tasks(DEFAULT_TASKS, FixtureModel(REGRESSED_REPLIES))
    assert all(not r.passed for r in results), "every regressed reply should fail"


def test_invented_file_contents_is_caught() -> None:
    """Regression guard for the num_ctx eviction bug's user-visible symptom."""
    task = next(t for t in DEFAULT_TASKS if t.id == "refusal-no-invented-file")
    result = run_task(task, FixtureModel(REGRESSED_REPLIES))
    assert not result.passed
    assert any("fabricate" in c.detail for c in result.checks if not c.passed)


def test_every_default_task_has_a_fixture() -> None:
    """A missing fixture would otherwise surface as a confusing KeyError in CI."""
    ids = {t.id for t in DEFAULT_TASKS}
    assert ids <= set(GOOD_REPLIES), f"missing good fixtures: {ids - set(GOOD_REPLIES)}"
    assert ids <= set(REGRESSED_REPLIES), f"missing bad fixtures: {ids - set(REGRESSED_REPLIES)}"


def test_default_task_ids_are_unique() -> None:
    ids = [t.id for t in DEFAULT_TASKS]
    assert len(ids) == len(set(ids))


def test_missing_fixture_raises_rather_than_scoring_zero() -> None:
    task = Task(id="nope", category=Category.CODEGEN, prompt="x", checks=())
    with pytest.raises(KeyError):
        list(FixtureModel({}).stream(task))


def test_model_error_is_captured_not_raised() -> None:
    """One broken task must not abort the whole run."""

    class Boom:
        def stream(self, task: Task) -> Iterator[str]:
            raise RuntimeError("ollama died")
            yield ""  # pragma: no cover

    task = Task(
        id="t",
        category=Category.CODEGEN,
        prompt="x",
        checks=(Check(kind="contains", value="anything"),),
    )
    result = run_task(task, Boom())
    assert result.error is not None
    assert "ollama died" in result.error
    assert not result.passed


def test_errored_task_fails_even_with_no_checks() -> None:
    """Zero checks must not let an errored task score as a pass."""

    class Boom:
        def stream(self, task: Task) -> Iterator[str]:
            raise RuntimeError("down")
            yield ""  # pragma: no cover

    result = run_task(Task(id="t", category=Category.CODEGEN, prompt="x", checks=()), Boom())
    assert not result.passed


def test_files_are_inlined_into_the_prompt() -> None:
    """File-grounded tasks must actually deliver the attachment."""
    seen: dict[str, str] = {}

    class Capture:
        def stream(self, task: Task) -> Iterator[str]:
            from inclave_eval.runner import _build_messages

            seen["content"] = _build_messages(task)[0]["content"]
            yield "ok"

    task = Task(
        id="t",
        category=Category.FILE_QA,
        prompt="what is in it?",
        checks=(),
        files={"a.csv": "name,rev\nacme,1"},
    )
    run_task(task, Capture())
    assert "a.csv" in seen["content"]
    assert "acme,1" in seen["content"]
    assert "what is in it?" in seen["content"]
