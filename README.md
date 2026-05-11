# InClave

> Drop a PDF, Excel, CSV, or code file. Ask a question. Run the answer.
> Locally, on macOS, with a local LLM and a sandbox for code execution.
> No cloud. No telemetry. Nothing leaves your machine.

[![CI](https://github.com/emretheus/inclave/actions/workflows/ci.yml/badge.svg)](https://github.com/emretheus/inclave/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)]()

![demo](demo.gif)

---

## What it does

InClave is a CLI for working with your own files using a **local** language
model. It pairs three things:

- **Local inference** via [Ollama](https://ollama.com/) — pick any model you have
  installed, queries never leave your machine.
- **Native macOS sandbox** ([Seatbelt](https://en.wikipedia.org/wiki/Seatbelt_(software)))
  so model-generated code runs in a jail with no network and a single read/write
  directory.
- **A workspace of your files** that the model can read — PDF, Excel, CSV,
  Markdown, text, and source code. Files are content-hashed local copies; your
  originals are never modified.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/emretheus/inclave/master/install.sh | sh
```

Or manually with [`uv`](https://docs.astral.sh/uv/):

```bash
brew install ollama
ollama serve &
ollama pull llama3.2

git clone https://github.com/emretheus/inclave.git
cd inclave
uv tool install --from packages/cli inclave-cli
```

> Requires macOS, Python 3.12+, and a running Ollama daemon.

## Quick start

```bash
# 1. First-run setup — creates ~/.inclave/{config.json,sessions/,log/,workspaces/}
inclave init

# 2. Choose a default model
inclave models list
inclave models use llama3.2

# 3. Add files to your local workspace
inclave files add ~/Documents/q3-report.pdf ~/Downloads/expenses.csv

# 4. Ask a one-shot question
inclave ask "what was the Q3 churn rate?"

# 5. Or have a conversation
inclave chat
```

Inside `chat`:

- **Drag a file** from Finder onto the prompt — it's attached automatically.
  Add a question on the same line and it's sent in one shot.
- Type **`/`** to open a command palette (↑/↓ to pick, Enter/Tab to insert).
- Type **`/run`** after the model writes a Python block — the code executes in
  the sandbox with your attached files mounted in. Output streams back into the
  conversation.
- Sessions autosave after every reply. Resume the last one with
  `inclave chat --resume`, or `/save <name>` mid-chat and list everything with
  `inclave sessions list`.

## Usage examples

**Analyze a spreadsheet without it leaving your machine**

```
$ inclave chat
●  inclave  llama3.2:latest  workspace: 0 files  workdir: ~/Downloads

›  ~/Downloads/expenses.csv  what categories are in this file?

  + expenses.csv  (added)

  Looking at the CSV, the categories are: coffee, lunch, gas.
```

**Have the model write code, then run it sandboxed against your data**

```
›  total spend by category, as a bar chart

  ```python
  import pandas as pd
  df = pd.read_csv("expenses.csv")
  df.groupby("category")["amount"].sum().plot.bar()
  ```

›  /run

  ┌── proposed code ────────────────────────────────────┐
  │ 1  import pandas as pd                              │
  │ 2  df = pd.read_csv("expenses.csv")                 │
  │ 3  df.groupby("category")["amount"].sum().plot.bar()│
  └─────────────────────────────────────────────────────┘
  workdir will contain: expenses.csv
  run in sandbox?  [y/N] y

  ran · exit 0 · 1.4s
```

The script ran in a temporary directory containing only your attached files,
with no network access, then the sandbox was torn down.

## Supported file types

| Type   | Extensions                                        | Notes                                                |
|--------|---------------------------------------------------|------------------------------------------------------|
| Text   | `.txt` `.md`                                      | Read as-is                                           |
| Tables | `.csv`                                            | First 1,000 rows as a markdown table                 |
| Excel  | `.xlsx` `.xls`                                    | Each sheet as a markdown table                       |
| PDF    | `.pdf`                                            | Text via `pypdf`                                     |
| Code   | `.py .js .ts .go .rs .java .sh .sql .json .yaml`… | Fenced Markdown so the model knows it's source code  |

Up to 5 files per session, 200 KB total extracted text, 100 KB per file.
Larger inputs are truncated with a clear marker.

## How privacy works

- The model is local. The CLI talks to Ollama over `127.0.0.1:11434`.
- The sandbox profile (`packages/sandbox/profiles/default.sb`) blocks network
  access, denies all file I/O outside the run's working directory, and applies
  CPU / memory / wall-clock limits via `RLIMIT`.
- Files in your workspace live at `~/.inclave/workspaces/default/` as
  content-hashed copies; deleting them is `inclave files clear` or
  `rm -rf ~/.inclave`.
- No telemetry, no analytics, no remote calls. CI has a guard that grep-checks
  for outbound HTTP to anything other than localhost.

## Status

`v0.1` in progress — a working demo of the core flow (workspace, file analysis,
chat, sandbox `/run`). Expect rough edges; APIs may change.

**macOS-only** by design: the sandbox depends on Seatbelt (`sandbox-exec`).
Linux support (via `bubblewrap`) is on the roadmap; Windows is out of scope.

## Configuration

Settings live in `~/.inclave/config.json`:

| Key                    | Default     | Purpose                                            |
|------------------------|-------------|----------------------------------------------------|
| `default_model`        | `null`      | Model used when `--model` isn't passed             |
| `sandbox_cpu_seconds`  | `30`        | CPU time limit per `/run`                          |
| `sandbox_memory_mb`    | `512`       | Memory limit per `/run`                            |
| `auto_run`             | `false`     | Skip the `y/N` prompt before `/run`                |

Edit with `inclave config set <key> <value>` or by hand.

Two global flags work on every subcommand:

- `--debug` — write operational logs (no message content) to
  `~/.inclave/log/inclave.log` (rotated at 10 MB × 3). Off by default.
- `--no-color` — disable ANSI colors. `NO_COLOR=1` env var works too.

## Development

```bash
git clone https://github.com/emretheus/inclave.git
cd inclave
uv sync --all-packages --all-extras

uv run pytest                   # 100+ tests
uv run ruff check .             # lint
uv run ruff format --check .    # format
uv run mypy packages shared     # type-check (strict)
```

The repo is a [`uv`](https://docs.astral.sh/uv/) workspace with three packages
plus a shared core:

```
packages/
  cli/          # Typer app, REPL, file parsers, prompts
  ollama/       # Local LLM inference + model management
  sandbox/      # macOS Seatbelt isolated executor
shared/
  inclave_core/ # Config, errors, workspace
```

## Authors

Built by:

- **Emre Ulgac** 
- **Emre Kocyigit**
- **Ibrahim Furkan Gulcan** 

See the [contributors page](https://github.com/emretheus/inclave/graphs/contributors)
for everyone who has contributed.

## Contributing

Issues and pull requests welcome. Please:

- Add tests for code you change. CI gates lint, format, type-check, and tests.
- Keep PRs small and focused; cross-package contract changes (anything in an
  `api.py`) need wider review.

## License

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
