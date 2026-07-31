# inclave-eval

Accuracy and latency benchmarks for the InClave chat pipeline.

Passing tests prove the code runs. This proves it *works* — that the model
answers from attached files, refuses when it has no file, and emits code blocks
the runner can actually extract.

## Two modes

| Mode | Command | Uses Ollama | Runs in CI |
|---|---|---|---|
| Fixture | `inclave-eval` | no | yes |
| Live | `inclave-eval --live` | yes | no |

Both score through identical logic; only the model backend differs.

**Fixture mode** replays recorded replies. Deterministic and fast, so it gates
every PR — it verifies the harness, scorers, and report, not model quality.

**Live mode** streams from a real local model and is the only mode that
produces real accuracy and latency numbers.

## Usage

```bash
inclave-eval                              # fixture run
inclave-eval --live --model llama3.2:3b   # real numbers
inclave-eval --live --json out/eval.json  # machine-readable results
inclave-eval --fail-under 80              # non-zero exit below 80% pass rate
```

## What it measures

Six tasks across four categories:

- **codegen** — generates working code in an extractable block
- **file_qa** — answers from attached file content
- **refusal** — declines when the answer isn't in the data
- **format** — emits blocks `python_blocks_in` can find

Latency is reported as **time-to-first-token** (median and p95) separately from
total duration, because a run can stream fast overall and still feel slow if the
model stalls before the first chunk. Fixture runs don't report latency — it
would be measuring string slicing.

## Why refusal tasks matter

`refusal-no-invented-file` encodes a bug this project shipped: when `num_ctx`
was left unset, Ollama silently evicted the system prompt, the "never invent
file contents" guard disappeared, and the model fabricated a config file. The
task fails on any fabricated block, in any language.

## Adding a task

Add a `Task` to `tasks/default.py` with a `rationale` naming the regression it
guards, then record replies in `tasks/fixtures.py` — one well-behaved
(`GOOD_REPLIES`) and one regressed (`REGRESSED_REPLIES`). A test asserts every
task has both, so a missing fixture fails loudly instead of erroring mid-run.
