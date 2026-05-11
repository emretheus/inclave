# InClave — your local AI assistant, in one CLI

> A **local-first, privacy-first AI assistant** for macOS. Talk to your PDFs,
> spreadsheets, CSVs, and code with a **local LLM via Ollama** — and let the
> model run Python code in a **Seatbelt sandbox** with no network access.
> No cloud, no telemetry, no API keys, no data leaves your machine.

[![CI](https://github.com/emretheus/inclave/actions/workflows/ci.yml/badge.svg)](https://github.com/emretheus/inclave/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)]()

![demo](demo-data/demo.gif)

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/emretheus/inclave/master/install.sh | sh
```

Then just:

```bash
inclave
```

That's it. On first run, InClave starts the Ollama daemon for you, lets you
pick a model from a curated list (`llama3.2`, `llama3.1:8b`,
`qwen2.5-coder:7b`, or your own), pulls it, and drops you into a chat.

> **Requires:** macOS, Python 3.12+. Ollama is auto-detected; if missing the
> CLI tells you to `brew install ollama`.

## What it does

- **Local LLM via [Ollama](https://ollama.com/)** — every prompt and response
  stays on `127.0.0.1`. No API keys, no rate limits, no usage caps.
- **Native macOS sandbox** ([Seatbelt](https://en.wikipedia.org/wiki/Seatbelt_(software)))
  — model-generated Python runs in a jail with **no network**, locked to a
  single read/write directory, with CPU/memory/wall-clock limits.
- **A workspace of your files** the model can read — PDF, Excel, CSV, Markdown,
  text, and source code. Originals are never modified; only content-hashed
  copies live under `~/.inclave/`.
- **Drop a file, ask a question.** Drag any file from Finder onto the chat
  prompt — it's attached automatically. Add a question on the same line to
  send everything in one shot.

## Quick demo

````text
$ inclave
●  inclave  qwen2.5-coder:7b  workspace: 0 files  workdir: ~/Downloads

›  ~/Downloads/mrr_2026.csv  print total mrr_usd growth in %

  + mrr_2026.csv  (added)

  ```python
  import pandas as pd
  df = pd.read_csv("mrr_2026.csv")
  total = (df["mrr_usd"].iloc[-1] - df["mrr_usd"].iloc[0]) / df["mrr_usd"].iloc[0] * 100
  print(f"Total MRR_USD growth: {total:.2f}%")
  ```

  ╭──────────── stdout ────────────╮
  │ Total MRR_USD growth: 96.06%
  ╰────────────────────────────────╯
  ran · exit 0 · 1.2s

  MRR_USD grew by approximately 96 % from September to April.
````

The python block ran **automatically** in a temporary sandbox: no network,
no escape to `~/.ssh`, output fed back to the model so the summary is
grounded in real stdout — not a prediction.

## Why InClave?

Cloud AI wants your files. Letting an LLM run code on your laptop is
convenient *and* dangerous. InClave keeps the model local and sandboxes
the execution — an **offline AI code interpreter** that respects your
filesystem.

## Inside the chat

- **Python blocks auto-run** in the sandbox; the model reads its own
  stdout and writes the follow-up.
- **Drop a path** from Finder, with or without a question on the same line.
- `/help` `/run` `/setup` `/model` `/save` `/files` `/clear` `/reset` —
  see `/help` for full descriptions.

Sessions autosave after every reply. Resume the last with
`inclave chat --resume`; `inclave sessions list` shows everything saved.

## Supported file types

| Type   | Extensions                                        | Notes                                |
|--------|---------------------------------------------------|--------------------------------------|
| Text   | `.txt` `.md`                                      | Read as-is                           |
| Tables | `.csv`                                            | First 1,000 rows as markdown         |
| Excel  | `.xlsx` `.xls`                                    | Each sheet as markdown               |
| PDF    | `.pdf`                                            | Text via `pypdf`                     |
| Code   | `.py .js .ts .go .rs .java .sh .sql .json .yaml`… | Fenced as source                     |

Limits: 5 files / 200 KB total / 100 KB per file. Excess is truncated.

## Privacy contract

- Talks only to `127.0.0.1:11434` (local Ollama). CI guard rejects any
  non-localhost URL in production code.
- Sandbox profile blocks network, denies file I/O outside the run dir,
  enforces CPU / memory / wall-clock rlimits.
- Workspace files live at `~/.inclave/workspaces/default/` as content-
  hashed copies. `inclave files clear` or `rm -rf ~/.inclave` wipes them.
- No telemetry, no analytics, no auto-update. Logs are off by default;
  `--debug` writes operational events only — **never** message content.

## Configuration

`~/.inclave/config.json` — edit by hand or with `inclave config set <key> <value>`:

| Key                    | Default | Purpose                                     |
|------------------------|---------|---------------------------------------------|
| `default_model`        | `null`  | Model used when `--model` isn't passed      |
| `sandbox_cpu_seconds`  | `30`    | CPU time limit per sandbox run              |
| `sandbox_memory_mb`    | `512`   | Memory limit per sandbox run                |

Global flags: `--debug` (operational logs only) and `--no-color`
(also via `NO_COLOR=1`).

## Status & platform

`v0.1`, macOS only — the sandbox depends on Seatbelt (`sandbox-exec`).
Core flow is stable; APIs may still change.

## Roadmap

- [ ] **Linux support** via [`bubblewrap`](https://github.com/containers/bubblewrap).
      Same policy (no network, single read/write directory, rlimits),
      different backend behind the same `inclave_sandbox.api` contract.
- [ ] **Windows support** via the WSL2 Linux backend, or — longer term —
      a native sandbox using AppContainer / Job Objects. Tracking issue
      welcome.
- [ ] Image attachments (drag a PNG into the prompt, send to a
      vision-capable local model).
- [ ] Per-project sandbox profile overrides (allow specific paths /
      domains for the rare workflow that legitimately needs them).
- [ ] Better long-context handling for big PDFs (chunking + retrieval
      across pages instead of the current 100 KB truncate).

## Manual install

Don't want to pipe `curl` into `sh`?

```bash
brew install ollama && ollama serve &
git clone https://github.com/emretheus/inclave.git && cd inclave
uv tool install --from packages/cli inclave-cli
```

## Development

```bash
uv sync --all-packages --all-extras
uv run pytest                   # 170+ tests
uv run ruff check . && uv run ruff format --check .
uv run mypy packages shared     # strict
```

A [`uv`](https://docs.astral.sh/uv/) workspace: `packages/cli` (Typer +
REPL), `packages/ollama` (inference), `packages/sandbox` (Seatbelt
executor), `shared/inclave_core` (config, sessions, logging).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — issues for non-trivial changes,
tests required, CI gates lint / format / type-check / coverage / the
no-outbound-HTTP guard.

## Authors

Built by:

- **Emre Ulgac**
- **Emre Kocyigit**
- **Ibrahim Furkan Gulcan**

See the [contributors page](https://github.com/emretheus/inclave/graphs/contributors)
for everyone who has contributed.

## License

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
