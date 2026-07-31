"""Check evaluation.

Scorers deliberately call the *product's* extraction helpers (rather than
reimplementing them) so a regression in block detection shows up as an eval
failure instead of being masked by a parallel implementation.
"""

from __future__ import annotations

import re

from inclave_cli.chat_engine import python_blocks_in

from .types import Check, CheckResult

# A fenced block in any language (or none). Deliberately broader than the
# product's python-only extractor — see the `code_block` branch below.
_ANY_FENCE_RE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)


def _apply(check: Check, reply: str) -> tuple[bool, str]:
    """Return (raw_match, detail) before negation is applied."""
    kind = check.kind

    if kind == "contains":
        hit = check.value.lower() in reply.lower()
        return hit, "" if hit else f"substring {check.value!r} not found"

    if kind == "exact":
        hit = reply.strip() == check.value.strip()
        return hit, "" if hit else "reply did not match expected text exactly"

    if kind == "regex":
        try:
            hit = re.search(check.value, reply, re.IGNORECASE | re.MULTILINE) is not None
        except re.error as e:
            # A malformed pattern is an authoring bug, not a model failure.
            # Surface it rather than silently scoring the task as failed.
            return False, f"invalid regex {check.value!r}: {e}"
        return hit, "" if hit else f"pattern {check.value!r} did not match"

    if kind == "code_block":
        # Any fenced block, whatever the language. `python_block` is too narrow
        # for refusal tasks: a model that invents a YAML or JSON config has
        # still fabricated file contents, and must not score as a refusal.
        hit = _ANY_FENCE_RE.search(reply) is not None
        return hit, "" if hit else "no fenced code block found"

    if kind in ("python_block", "no_python_block"):
        blocks = python_blocks_in(reply)
        has = len(blocks) > 0
        # `no_python_block` is expressed as its own kind for readability at the
        # task-definition site; it is just the inverse observation.
        want = kind == "python_block"
        hit = has if want else not has
        if hit:
            return True, ""
        return False, (
            "no python block found" if want else f"unexpected python block ({len(blocks)})"
        )

    # Unknown kind: fail loudly rather than defaulting to pass.
    return False, f"unknown check kind {kind!r}"


def run_check(check: Check, reply: str) -> CheckResult:
    raw, detail = _apply(check, reply)
    passed = (not raw) if check.negate else raw
    if passed:
        detail = ""
    elif check.negate and raw:
        detail = check.describe or f"expected NOT to match {check.value!r}, but it did"
    elif check.describe:
        detail = f"{check.describe}: {detail}" if detail else check.describe
    return CheckResult(check=check, passed=passed, detail=detail)


def run_checks(checks: tuple[Check, ...], reply: str) -> tuple[CheckResult, ...]:
    return tuple(run_check(c, reply) for c in checks)
