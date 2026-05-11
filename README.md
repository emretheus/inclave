# InClave — your local AI assistant, in one CLI

> A **local-first, privacy-first AI assistant** for macOS. Talk to your PDFs,
> spreadsheets, CSVs, and code with a **local LLM via Ollama** — and let the
> model run Python code in a **Seatbelt sandbox** with no network access.
> No cloud, no telemetry, no API keys, no data leaves your machine.

[![CI](https://github.com/emretheus/inclave/actions/workflows/ci.yml/badge.svg)](https://github.com/emretheus/inclave/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)]()

![demo](demo.gif)

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

```
$ inclave
●  inclave  llama3.2  workspace: 0 files  workdir: ~/Downloads

›  ~/Downloads/expenses.csv  total spend by category, as a bar chart

  + expenses.csv  (added)

  ```python
  import pandas as pd
  df = pd.read_csv("expenses.csv")
  df.groupby("category")["amount"].sum().plot.bar()
  ```

›  /run
  ┌── proposed code ─────────────────────────────────────┐
  │ 1  import pandas as pd                               │
  │ 2  df = pd.read_csv("expenses.csv")                  │
  │ 3  df.groupby("category")["amount"].sum().plot.bar() │
  └──────────────────────────────────────────────────────┘
  workdir will contain: expenses.csv
  run in sandbox? [y/N] y

  ran · exit 0 · 1.4s
```

The script ran in a temporary directory containing only your attached files,
with no network access, then the sandbox was torn down.

## Why InClave?

You probably already know:

- Cloud AI assistants want your files in their data center.
- Letting an LLM run code on your machine is convenient — and dangerous.

InClave splits the difference. The model is local, so nothing leaves the
machine. The execution is sandboxed, so the model can't read your `~/.ssh`,
hit your VPN, exfiltrate to the network, or write outside the run directory.

It's an **offline AI code interpreter** that respects your filesystem.

## Inside the chat

- **Drop a path** from Finder, with or without a question on the same line.
- **`/help`** — list every slash command.
- **`/run`** — execute the last Python block the model wrote (asks `y/N`).
- **`/setup`** — re-run the interactive setup (start Ollama, pick a model).
- **`/model <name>`** — switch model mid-chat.
- **`/save <name>`** — name and save the current conversation.
- **`/files`** — list attached files.
- **`/clear`** / **`/reset`** — wipe history (and optionally files).

Sessions autosave after every reply. Resume the last with
`inclave chat --resume`; `inclave sessions list` shows everything saved.

## Supported file types

| Type   | Extensions                                        | Notes                                            |
|--------|---------------------------------------------------|--------------------------------------------------|
| Text   | `.txt` `.md`                                      | Read as-is                                       |
| Tables | `.csv`                                            | First 1,000 rows as a markdown table             |
| Excel  | `.xlsx` `.xls`                                    | Each sheet as a markdown table                   |
| PDF    | `.pdf`                                            | Text via `pypdf`                                 |
| Code   | `.py .js .ts .go .rs .java .sh .sql .json .yaml`… | Fenced markdown so the model knows it's source   |

Up to 5 files per session, 200 KB total extracted text, 100 KB per file.
Larger inputs are truncated with a clear marker.

## Privacy contract

- The CLI only talks to `127.0.0.1:11434` (the local Ollama daemon). CI has a
  guard that fails the build if any production module references a
  non-localhost URL.
- The sandbox profile (`packages/sandbox/profiles/default.sb`) blocks network
  access, denies all file I/O outside the run directory, and applies CPU /
  memory / wall-clock limits via `RLIMIT`.
- Files in your workspace live at `~/.inclave/workspaces/default/` as
  content-hashed copies. Delete everything with `inclave files clear` or
  `rm -rf ~/.inclave`.
- No telemetry, no analytics, no auto-update, no remote calls.
- Logs are off by default. `--debug` writes operational events (command
  names, timing, exit codes — **never** message content) to
  `~/.inclave/log/inclave.log`.

## Configuration

Settings live in `~/.inclave/config.json`:

| Key                    | Default     | Purpose                                            |
|------------------------|-------------|----------------------------------------------------|
| `default_model`        | `null`      | Model used when `--model` isn't passed             |
| `sandbox_cpu_seconds`  | `30`        | CPU time limit per `/run`                          |
| `sandbox_memory_mb`    | `512`       | Memory limit per `/run`                            |
| `auto_run`             | `false`     | Skip the `y/N` prompt before `/run`                |

Edit with `inclave config set <key> <value>` or by hand.

Global flags (work on every subcommand):

- `--debug` — write operational logs to `~/.inclave/log/inclave.log`.
- `--no-color` — disable ANSI colors. `NO_COLOR=1` works too.

## Status & platform

`v0.1` — the core flow (workspace, file analysis, chat, sandbox `/run`,
sessions) works end-to-end. APIs may still change.

**macOS only by design**: the sandbox depends on Seatbelt (`sandbox-exec`).
Linux support (via `bubblewrap`) is on the roadmap. Windows is out of scope.

## Manual install

If you'd rather not pipe `curl` into `sh`:

```bash
brew install ollama
ollama serve &
ollama pull llama3.2

git clone https://github.com/emretheus/inclave.git
cd inclave
uv tool install --from packages/cli inclave-cli
```

## Development

```bash
git clone https://github.com/emretheus/inclave.git
cd inclave
uv sync --all-packages --all-extras

uv run pytest                   # 170+ tests
uv run ruff check .             # lint
uv run ruff format --check .    # format
uv run mypy packages shared     # type-check (strict)
```

Repo layout (a [`uv`](https://docs.astral.sh/uv/) workspace):

```
packages/
  cli/          # Typer app, REPL, file parsers, prompts, onboarding
  ollama/       # Local LLM inference + model management
  sandbox/      # macOS Seatbelt isolated executor
shared/
  inclave_core/ # Config, errors, workspace, sessions, logging
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Short version:

- Open an issue first for non-trivial changes.
- Tests are required on every PR. CI gates lint, format, type-check,
  coverage, and the no-outbound-HTTP guard.

## Authors

Built by:

- **Emre Ulgac**
- **Emre Kocyigit**
- **Ibrahim Furkan Gulcan**

See the [contributors page](https://github.com/emretheus/inclave/graphs/contributors)
for everyone who has contributed.

## License

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
