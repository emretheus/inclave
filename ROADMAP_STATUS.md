# Roadmap Status

_Checked against master, 2026-07-31._

## Done

| # | Item | Where |
|---|---|---|
| **P0** | Fix `sessions.py` | `0566e33b` — module restored, imports clean |
| **P1** | Eval & benchmarks | `packages/eval` — task set, scorers, CI gate |
| **P2** | Latency instrumentation | `packages/eval/timing.py` — TTFT + p95 |
| **P2** | Fix streaming cancel | PR #22 — `is_cancelled` checked in `chat.py` |

The roadmap listed the first and last of these as outstanding. Both had
already landed; the doc was written before those merges.

## Still open

| # | Item | Effort | Note |
|---|---|---|---|
| **P1** | Parsed-file cache | S | No caching in any source module yet |
| **P1** | RAG for large files | L | Files >100 KB still truncated |
| **P1** | Context window mgmt | M | Issue #17, unblocked since #16 closed |
| **P2** | Confirm-before-run | S | Not started |
| **P2** | Linux sandbox | M | Bubblewrap backend |

## Current numbers

- 262 tests passing (was 221 before eval)
- 83% coverage, strict mypy clean across 86 files
- Eval: 6 tasks, 4 categories, gates CI at 100% in fixture mode

## What to do next

**Parsed-file cache (P1, S).** Cheapest remaining win and it now has a
way to prove itself — `inclave-eval --live` reports time-to-first-token,
so the speedup from not re-parsing the same PDF every turn becomes a
number instead of a claim.

**Context window management (P1, M).** Issue #17 is well-specified and
unblocked. Phase 1 (warn at 80%) ships independently of the sliding
window and summarization phases.

**RAG (P1, L).** Biggest item, best saved for last of the P1s — it
benefits most from the cache and the eval baseline being in place first.

## Ideas beyond the current list

Small, in roughly the order they'd pay off:

- **Eval regression tracking** — commit `--json` output per release so
  accuracy and latency trends are visible across versions, not just per run.
- **More eval tasks** — multi-turn memory, larger files, malformed input.
  The harness takes new tasks in a few lines each.
- **Sandbox escape tests** — assert network calls and writes outside the
  workspace actually fail. The profile exists; nothing proves it holds.
- **Model comparison** — run the eval across several local models and
  publish the table. Directly answers "which model should I use?"
- **Golden-file CLI tests** — snapshot terminal output so UI regressions
  surface in CI.
- **Structured error taxonomy** — the two shipped P0s were both silent
  failures; a shared error path would make that class visible by default.

## Note on CI

GitHub Actions is currently blocked: every job fails in seconds with
_"the job was not started because your account is locked due to a billing
issue."_ No workflow has actually run since 2026-07-28, so recent merges
are unverified by CI. Everything above was verified locally instead.
