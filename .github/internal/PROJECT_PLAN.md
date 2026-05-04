# Enclave Code — Project Plan

> Local-first, privacy-preserving CLI for macOS that combines **isolated code execution** with **local Ollama models** to help users do daily work over their own files (PDF, Excel, CSV, text) — no cloud, no telemetry, no data leaves the machine.

---

## 1. Vision

Most "AI assistant" workflows today require shipping user files and prompts to remote APIs. Enclave Code flips that: everything runs on the user's MacBook. The CLI is the only interface. The user picks a local Ollama model, points the CLI at a file, asks a question or asks the model to run code over the file, and the code is executed inside a macOS sandbox so the model can't touch anything outside the working directory.

The product is the combination of three things that are individually unremarkable but together unique:

1. **Local LLM** (Ollama) — private inference.
2. **Native macOS sandbox** (Seatbelt / `sandbox-exec`) — model-generated code can't escape the working directory or reach the network.
3. **File-aware CLI** — Excel, PDF, CSV, text are first-class context, ingested and presented to the model as structured input.

---

## 2. Goals & Non-Goals

### Goals (v0.1)
- **macOS-only** CLI installable via `pipx` or `uv tool install`.
- Interactive REPL: `enclave chat` with file context attached.
- One-shot mode: `enclave ask "..." --file foo.xlsx`.
- Sandbox: model can generate Python code; code runs inside a Seatbelt jail with no network and a single read/write directory.
- Ollama: list, pull, set default, switch models from CLI.
- File ingestion: `.pdf`, `.xlsx`, `.xls`, `.csv`, `.txt`, `.md`.
- Tests + CI on every PR.

### Non-Goals (v0.1)
- Linux / Windows support.
- A web UI, TUI dashboard, or daemon.
- Cloud sync, accounts, telemetry.
- Fine-tuning or training.
- Multi-user / server deployment.
- RAG over giant corpora (single-file context for v0.1).

---

## 3. Tech Stack

| Concern              | Choice                          | Why |
|----------------------|----------------------------------|-----|
| Language             | Python 3.12                      | Best ecosystem for Ollama, PDF, Excel; team velocity |
| CLI framework        | Typer (+ Rich for output)        | Type-hint driven, ergonomic, modern |
| REPL line editing    | `prompt_toolkit`                 | History, multi-line input, key bindings |
| Package / workspace  | `uv` workspaces                  | Fast, modern, native monorepo support |
| Sandbox              | `sandbox-exec` (Seatbelt) + `setrlimit` | Native macOS, no Docker dep |
| LLM                  | `ollama` Python client           | Official, supports streaming |
| PDF                  | `pypdf` + `pdfplumber` (fallback) | Handles most PDFs incl. tables |
| Excel                | `openpyxl` + `pandas`            | Read/write, formulas, multi-sheet |
| Test framework       | `pytest` + `pytest-cov`          | Standard |
| Lint / format        | `ruff`                           | One tool, fast |
| Type check           | `mypy --strict` per package      | Catch contract drift between teams |
| CI                   | GitHub Actions (macos-latest)    | Sandbox tests need real macOS runner |

**Rejected alternatives** (recorded so we don't relitigate):
- *Rust*: better sandbox primitives, but slower team velocity and weaker file-parsing libs.
- *Docker for sandbox*: heavy dep, requires Docker Desktop install, not "native".
- *Node/oclif*: weaker Ollama and file-parsing ecosystem.

---

## 4. Repository Layout (monorepo)

```
enclave-code/
├── .github/
│   └── workflows/
│       ├── ci.yml                  # lint + test on every PR
│       └── release.yml             # later
├── packages/
│   ├── cli/                        # Emre  — entrypoint, REPL, file ingest, command routing
│   │   ├── src/enclave_cli/
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── sandbox/                    # Ulgac — secure code execution
│   │   ├── src/enclave_sandbox/
│   │   ├── profiles/               # .sb Seatbelt profile templates
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── ollama/                     # Ibrahim — model config & inference
│       ├── src/enclave_ollama/
│       ├── tests/
│       └── pyproject.toml
├── shared/
│   └── enclave_core/               # shared types, config schema, logging
│       ├── src/enclave_core/
│       └── tests/
├── .github/internal/tasks/         # per-member breakdowns (internal)
│   ├── ULGAC.md
│   ├── EMRE.md
│   └── IBRAHIM.md
├── pyproject.toml                  # uv workspace root
├── uv.lock
├── PROJECT_PLAN.md                 # this file
└── .gitignore
```

Each package is independently installable, has its own `pyproject.toml`, and its own `tests/` directory. The root `pyproject.toml` declares the workspace.

---

## 5. Module Contracts

These are the **frozen interfaces** between members. Changing them requires a PR that all three approve. This is what allows parallel work.

### 5.1 `enclave_sandbox` (Ulgac → exposes to CLI)

```python
# enclave_sandbox/api.py
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class SandboxPolicy:
    workdir: Path                 # only readable/writable directory
    allow_network: bool = False   # always False in v0.1
    cpu_seconds: int = 30
    memory_mb: int = 512
    wall_clock_seconds: int = 60

@dataclass(frozen=True)
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    duration_ms: int

def execute_python(code: str, policy: SandboxPolicy) -> ExecutionResult: ...
def execute_shell(command: str, policy: SandboxPolicy) -> ExecutionResult: ...
```

### 5.2 `enclave_ollama` (Ibrahim → exposes to CLI)

```python
# enclave_ollama/api.py
from dataclasses import dataclass
from typing import Iterator

@dataclass(frozen=True)
class ModelInfo:
    name: str
    size_bytes: int
    family: str
    parameter_count: str         # "7B", "13B", etc.
    is_default: bool

def list_models() -> list[ModelInfo]: ...
def pull_model(name: str) -> Iterator[str]: ...   # yields progress lines
def remove_model(name: str) -> None: ...
def set_default(name: str) -> None: ...
def get_default() -> str | None: ...

def generate(prompt: str, *, model: str | None = None, system: str | None = None) -> str: ...
def stream(prompt: str, *, model: str | None = None, system: str | None = None) -> Iterator[str]: ...
```

### 5.3 `enclave_core` (shared)

```python
# enclave_core/config.py
from pathlib import Path
from pydantic import BaseModel

class Config(BaseModel):
    default_model: str | None = None
    sandbox_cpu_seconds: int = 30
    sandbox_memory_mb: int = 512
    auto_run: bool = False                  # /run requires y/n unless True
    save_history: bool = True               # persist last chat session
    debug_log: bool = False                 # write ~/.enclave/log/enclave.log

def load_config() -> Config: ...            # reads ~/.enclave/config.toml
def save_config(cfg: Config) -> None: ...
```

```python
# enclave_core/errors.py
class EnclaveError(Exception): ...                  # base for all package errors
class ConfigError(EnclaveError): ...
class SandboxError(EnclaveError): ...               # raised by enclave_sandbox
class OllamaError(EnclaveError): ...                # raised by enclave_ollama
class OllamaUnavailableError(OllamaError): ...
class CLIError(EnclaveError): ...                   # raised by enclave_cli
```

Every package raises subclasses of `EnclaveError`. The CLI catches `EnclaveError` at the top level and prints `error.message` cleanly; only `--debug` shows tracebacks.

CLI consumes both sandbox and ollama. Sandbox and Ollama do **not** depend on each other — the CLI is the only orchestrator. This keeps blast radius small and makes each package independently testable.

---

## 6. CLI Surface (v0.1)

```
enclave init                                # create ~/.enclave/{config.toml,sessions/,log/}
enclave config show
enclave config set <key> <value>

enclave models list
enclave models pull <name>                  # streams progress
enclave models remove <name>
enclave models use <name>                   # set default

enclave chat [--model NAME] [--file PATH ...] [--resume] [-y|--auto-run]
enclave ask "question" [--model NAME] [--file PATH ...]
enclave run <file.py>                       # execute a script in sandbox
```

**Workdir = current working directory.** Whatever directory the user invokes `enclave chat` (or `ask`/`run`) from is the sandbox's read/write root. This matches shell convention and makes "use it on a project" obvious. The sandbox profile is rendered with that directory baked in.

Global flags: `--debug` (verbose tracebacks + write to `~/.enclave/log/enclave.log`), `--no-color`.

Inside `chat`, slash commands:
- `/file <path>` — attach another file to context
- `/files` — list currently attached files
- `/model <name>` — switch model mid-session
- `/run` — execute the last code block the model produced (asks y/n unless `--auto-run`)
- `/clear` — clear conversation history (keeps file context)
- `/reset` — clear everything including file context
- `/save <name>` — save current session under a name (MVP: optional, see §15)
- `/help`
- `/exit` (also Ctrl+D)

REPL key bindings: `Ctrl+C` cancels the current model stream and returns to prompt; double `Ctrl+C` exits. `Up`/`Down` walks history. Multi-line input via `Esc, Enter` or trailing `\`.

---

## 7. Testing Strategy

**Hard rule: every PR adds tests for the code it touches. CI blocks merges that don't.**

| Layer        | Tooling                  | Where                         |
|--------------|--------------------------|-------------------------------|
| Unit         | pytest                   | `packages/*/tests/`           |
| Integration  | pytest with real Ollama  | `tests/integration/` (root)   |
| Sandbox      | pytest + real `sandbox-exec` | `packages/sandbox/tests/` |
| End-to-end   | pytest invoking `enclave` CLI | `tests/e2e/`             |

### Coverage requirements
- Per-package coverage **≥ 80%** (enforced in CI).
- Sandbox package **≥ 90%** — security-critical, escape attempts must be tested.

### CI workflow (`.github/workflows/ci.yml`)
- Triggers: `push` to any branch, `pull_request` to `master`.
- Matrix: `macos-latest` (sandbox tests need real macOS).
- Steps: `uv sync` → `ruff check` → `mypy` → `pytest --cov` → coverage gate.
- PRs to `master` are blocked unless: all checks pass, coverage thresholds met, at least one approval from a member who didn't write the code.

### Sandbox-specific tests (Ulgac owns)
Adversarial test suite — these MUST exist:
- Code attempts to read `~/.ssh/id_rsa` → blocked.
- Code attempts to `curl` the network → blocked.
- Code attempts to `fork`-bomb → killed by rlimit.
- Code attempts to write outside workdir → blocked.
- Code legitimately reads the workdir file → succeeds.
- Code exceeds wall-clock → killed and reported `timed_out=True`.

---

## 8. Branching & PR Workflow

- `master` is protected. No direct pushes.
- Feature branches: `<member>/<short-desc>`, e.g. `ulgac/seatbelt-profile`, `emre/repl-loop`, `ibrahim/ollama-stream`.
- One PR = one logical change. Keep them small.
- PR template requires: *what changed*, *why*, *how tested*.
- Each package's owner is the default reviewer for changes inside their package. Cross-package contract changes (anything in `api.py`) require all three approvals.

---

## 9. Milestones

### M0 — Scaffolding (week 1)
- Monorepo layout, `uv` workspace, `pyproject.toml`s.
- CI workflow runs (even with empty tests).
- All three packages exist with stub `api.py` matching §5.
- README + this plan committed.

### M1 — Walking skeleton (week 2)
- `enclave init`, `enclave config`, `enclave models list/use`.
- `enclave ask "hello"` returns a real response from a hardcoded model.
- Sandbox can execute `print("hello")` and return result.
- CI green.

### M2 — Vertical slice (week 3–4)
- `enclave chat` REPL works (streaming, history, Ctrl+C cancel).
- File ingestion for PDF + CSV + Excel with the limits in §14.
- `/run` extracts last code block, shows it in a syntax-highlighted panel, asks `Run this in sandbox? [y/N]`, executes on confirm, prints result.
- Sandbox ships with the curated runtime described in §13.
- Adversarial sandbox test suite passes.
- Session auto-save + `--resume` works (§15).

### M3 — Polish + 0.1 release (week 5)
- `enclave models pull/remove` with progress.
- Streaming responses in REPL.
- Error messages are human.
- README install instructions verified end-to-end.
- Tag `v0.1.0`.

---

## 10. Owners

| Member  | Package                    | Primary deliverable |
|---------|----------------------------|---------------------|
| Ulgac   | `packages/sandbox`         | Seatbelt-based isolated executor |
| Emre    | `packages/cli` + `shared/` | CLI shell, REPL, file ingestion, config |
| Ibrahim | `packages/ollama`          | Ollama integration & model management |

Cross-cutting (owned jointly): `.github/workflows/`, root `pyproject.toml`, `PROJECT_PLAN.md`, integration tests under `tests/`.

Per-member task breakdowns are kept internally under `.github/internal/tasks/`.

---

## 11. Resolved Decisions (MVP)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Seatbelt profile shipped as a `.sb` file under `packages/sandbox/profiles/`, rendered with `(workdir)` substitution at runtime. | Auditable in source control. |
| 2 | Ollama availability checked once per CLI invocation via a precondition decorator on commands that need it. On failure, print one clear install/start hint and exit 1. | Avoids per-call latency, single clean error message. |
| 3 | `enclave run -` reads code from stdin. | Composes well with Unix pipelines. |
| 4 | Config file: TOML at `~/.enclave/config.toml`. | Human-readable, comments allowed. |
| 5 | License: **MIT** (decide before first public push if this changes). | Permissive, simple, common for tooling. |
| 6 | Workdir = current working directory at invocation time. | Matches shell convention; makes "run on this project" obvious. |
| 7 | `/run` requires `y/N` confirmation by default; `--auto-run` / `auto_run=true` in config skips it. | Sandbox limits damage but explicit consent is still right for MVP. |
| 8 | Sandbox ships with a curated, frozen Python runtime (§13). | Without this, model-generated code fails on missing imports. No `pip install` available because no network. |
| 9 | Multi-file ingestion capped at 5 files, 200 KB extracted text total (§14). | Predictable token budget; clear truncation behavior. |
| 10 | Sessions auto-save to `~/.enclave/sessions/last.json`; `enclave chat --resume` reloads. Named sessions are post-MVP. | One slot is enough to feel useful; no UX overhead. |
| 11 | All package errors subclass `EnclaveError`; CLI catches at top-level and prints `error.message`. `--debug` shows tracebacks. | Clean UX, easy debugging. |
| 12 | Single workspace version in root `pyproject.toml`; all packages bumped together. | Simpler than per-package SemVer for MVP. |
| 13 | No telemetry, no auto-update. Updates via `uv tool upgrade enclave-code`. | Aligns with privacy promise. |

---

## 12. MVP User Experience

### 12.1 First-run flow (60 seconds to value)

```
$ brew install ollama && ollama serve &        # one-time, user does themselves
$ uv tool install enclave-code
$ enclave init
✓ created ~/.enclave/config.toml
✓ created ~/.enclave/sessions/
no default model set yet — run: enclave models pull llama3.2 && enclave models use llama3.2

$ enclave models pull llama3.2
pulling manifest ✓
downloading 4.7 GB ████████████░░░░░░░  62%  ETA 1m12s
✓ pulled llama3.2

$ enclave models use llama3.2
✓ default model: llama3.2

$ cd ~/Downloads
$ enclave chat --file expenses.xlsx
attached: expenses.xlsx (3 sheets, 1,247 rows)
model: llama3.2 · workdir: ~/Downloads · /help for commands

> what's my total spend on coffee in March?
your March coffee spend was $84.20 across 11 transactions.

> write python that plots monthly totals as a bar chart and saves to monthly.png
[code panel showing pandas + matplotlib snippet]

> /run
Run this in sandbox? [y/N] y
[sandbox stdout] saved monthly.png (37 KB)
[sandbox] exit 0 · 1.4s

> /exit
session saved (resume with: enclave chat --resume)
```

That entire flow is the MVP. If any step in this transcript doesn't work end-to-end, we are not done.

### 12.2 REPL look and feel

- Prompt: `> ` in cyan. While model is streaming: dim spinner on the left edge until first token, then tokens stream inline.
- Code blocks in model output are rendered with Rich syntax highlighting, framed in a thin panel, with a faint label `python` (or other language).
- `[sandbox]` output is shown in a separate Rich Panel labeled `sandbox` with stdout (default) and stderr (red) sections.
- Errors are one-line, plain, e.g. `error: Ollama is not running. Start it with: ollama serve`.
- All Rich output respects `--no-color` and `NO_COLOR` env var.

### 12.3 One-shot flow

```
$ enclave ask "summarize this report in 5 bullets" --file Q3-report.pdf
[streamed answer]
```

No REPL, no session save, exits when done. Suitable for piping into other tools.

### 12.4 Script execution flow

```
$ enclave run plot.py                  # runs plot.py in sandbox at $PWD
$ cat plot.py | enclave run -          # same, from stdin
```

No model involved. This is the "use the sandbox directly" escape hatch.

---

## 13. Sandbox Runtime Environment

The sandbox package ships a **frozen, curated Python runtime** so model-generated code has the libraries it predictably wants. Because the sandbox has no network, the model cannot `pip install`. The runtime is locked at build time via `uv lock`.

### 13.1 Bundled libraries (MVP)

| Purpose       | Library    |
|---------------|------------|
| DataFrames    | `pandas`   |
| Numerics      | `numpy`    |
| Excel         | `openpyxl` |
| PDF (read)    | `pypdf`    |
| Plotting      | `matplotlib` (Agg backend; no display) |
| Stdlib only   | `csv`, `json`, `pathlib`, `re`, `datetime`, `statistics` |

That's it for v0.1. No `requests`, `httpx`, `scipy`, `scikit-learn`, `torch`. Adding to this list is a deliberate decision — opens a PR that updates this section, the lock file, and the system prompt that tells the model what's available.

### 13.2 System prompt awareness

The CLI's system prompt (owned by Emre, lives in `enclave_cli/prompts.py`) explicitly tells the model: *"When you write Python to be executed, you may import only: pandas, numpy, openpyxl, pypdf, matplotlib, plus the Python stdlib. Network access is blocked. The current working directory is the only readable/writable location."*

This single instruction prevents 90% of "code that won't run" failures.

### 13.3 Where the runtime lives

The sandbox package owns its own `uv`-managed venv at `packages/sandbox/runtime/`. The Seatbelt jail invokes `runtime/bin/python3` rather than the system Python. This isolates user-installed Python state from sandbox execution.

---

## 14. File & Context Strategy

### 14.1 Limits (MVP)

- Max 5 files attached per session.
- Max 200 KB total *extracted text* across all files (≈ 50K tokens, leaves headroom for typical 8K context windows).
- Per-file extracted text capped at 100 KB; over that, truncate with a clear warning shown to the user *and* a marker in the prompt: `[... truncated, X KB omitted ...]`.

### 14.2 Parsing rules

- **PDF** — text via `pypdf`. If a page has < 50 chars and the PDF has tables (heuristic: fitz/pdfplumber detects), fall back to `pdfplumber` for that page only.
- **Excel** — each sheet rendered as a markdown table, prefaced with `## Sheet: <name> (rows × cols)`. Numeric formatting preserved; formulas resolved to values.
- **CSV** — first 1,000 rows rendered as a markdown table; header always preserved. If truncated, append `(showing first 1,000 of N rows)`.
- **TXT/MD** — read as-is.
- **Unknown extension** — refuse with a clear error listing supported types.

### 14.3 Prompt assembly

```
<system prompt: role + tool/runtime info>

<file marker> path/to/file1.xlsx
<extracted content>

<file marker> path/to/file2.pdf
<extracted content>

<conversation history>

<latest user message>
```

The file blocks are stable across turns (cached) so attaching files doesn't multiply token cost on every turn.

---

## 15. Sessions, History, Errors, Logging

### 15.1 Sessions (MVP: one slot)

- `enclave chat` autosaves to `~/.enclave/sessions/last.json` after every assistant turn.
- `enclave chat --resume` reloads the last session (messages + attached file paths). If a previously-attached file no longer exists, drop it with a warning.
- `/clear` wipes conversation but keeps file context. `/reset` wipes both.
- Named sessions, listing, deletion are **post-MVP**.

Schema:
```json
{
  "version": 1,
  "model": "llama3.2",
  "workdir": "/abs/path",
  "files": ["/abs/path/foo.xlsx"],
  "messages": [{"role": "user|assistant", "content": "...", "ts": "ISO8601"}]
}
```

### 15.2 Errors

- Every package raises `EnclaveError` subclasses (§5.3).
- CLI top-level catches `EnclaveError` → prints `error: <message>` and exits with a non-zero code mapped per error class.
- Unhandled exceptions print `internal error: <type>: <message> (run with --debug for traceback)`.
- Exit codes: `0` ok, `1` user-facing error, `2` config error, `3` Ollama unavailable, `4` sandbox error, `99` internal.

### 15.3 Logging

- **Conversations are not logged anywhere by default.** This is part of the privacy promise.
- `--debug` writes operational logs (no message content) to `~/.enclave/log/enclave.log`, rotated at 10 MB, max 3 files.
- No analytics, no crash reporting, no remote calls — ever. CI has a guard test that greps for outbound HTTP to non-localhost.

---

## 16. Out of Scope for MVP (explicitly)

So we don't drift:
- Named/multi-session management, conversation search, export.
- RAG / vector embeddings / retrieval over multiple documents.
- Image input or image generation.
- Voice in or out.
- Plugin / extension system.
- Custom Seatbelt profiles per project.
- Auto-starting Ollama (we detect and instruct, we don't manage).
- Any GUI of any kind.
- Tool/function calling beyond `/run`.

Anything in this list that someone wants is a v0.2+ conversation with all three members.
