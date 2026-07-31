from __future__ import annotations

from inclave_eval.scoring import run_check, run_checks
from inclave_eval.types import Check


def test_contains_is_case_insensitive() -> None:
    assert run_check(Check(kind="contains", value="FizzBuzz"), "prints fizzbuzz").passed


def test_contains_reports_missing_substring() -> None:
    r = run_check(Check(kind="contains", value="210"), "the answer is 460")
    assert not r.passed
    assert "210" in r.detail


def test_regex_matches_multiline() -> None:
    assert run_check(Check(kind="regex", value=r"def\s+fizzbuzz"), "x\ndef fizzbuzz(n):").passed


def test_invalid_regex_fails_loudly_instead_of_passing() -> None:
    """An authoring typo must not silently score as a model failure."""
    r = run_check(Check(kind="regex", value="(unclosed"), "anything")
    assert not r.passed
    assert "invalid regex" in r.detail


def test_python_block_detected() -> None:
    reply = "here:\n\n```python\nprint(1)\n```\n"
    assert run_check(Check(kind="python_block"), reply).passed


def test_python_block_absent_when_only_prose() -> None:
    assert not run_check(Check(kind="python_block"), "just use text[::-1]").passed


def test_negate_inverts_the_result() -> None:
    """Refusal tasks depend on this: 'must NOT fabricate a block'."""
    reply = "```python\napi_key = 'sk-live'\n```"
    assert not run_check(Check(kind="python_block", negate=True), reply).passed
    assert run_check(Check(kind="python_block", negate=True), "I don't have that file").passed


def test_code_block_catches_non_python_fences() -> None:
    """A fabricated YAML config is still fabricated file contents.

    Regression guard: `python_block` alone missed this, letting a model that
    invented a config file score as a correct refusal.
    """
    yaml_reply = "```yaml\napi_key: sk-live-1234\n```"
    assert run_check(Check(kind="code_block"), yaml_reply).passed
    assert not run_check(Check(kind="python_block"), yaml_reply).passed
    # Negated, this is the refusal guard: must fail on fabricated YAML.
    assert not run_check(Check(kind="code_block", negate=True), yaml_reply).passed


def test_code_block_ignores_prose() -> None:
    assert not run_check(Check(kind="code_block"), "I don't have that file.").passed


def test_no_python_block_kind() -> None:
    assert run_check(Check(kind="no_python_block"), "no code here").passed
    assert not run_check(Check(kind="no_python_block"), "```python\nx=1\n```").passed


def test_exact_ignores_surrounding_whitespace() -> None:
    assert run_check(Check(kind="exact", value="210"), "  210\n").passed


def test_unknown_kind_fails_rather_than_passing() -> None:
    r = run_check(Check(kind="bogus", value="x"), "anything")  # type: ignore[arg-type]
    assert not r.passed
    assert "unknown check kind" in r.detail


def test_describe_is_surfaced_on_failure() -> None:
    r = run_check(Check(kind="contains", value="210", describe="120 + 90 = 210"), "460")
    assert "120 + 90 = 210" in r.detail


def test_run_checks_preserves_order() -> None:
    checks = (Check(kind="contains", value="a"), Check(kind="contains", value="zzz"))
    out = run_checks(checks, "a b c")
    assert [c.passed for c in out] == [True, False]
