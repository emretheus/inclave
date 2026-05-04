# Tasks — Emre (CLI Shell, REPL, File Ingestion, Config)

**Packages:** `packages/cli` — `enclave_cli`, plus `shared/enclave_core`
**Goal:** Build the only thing the user actually sees — the CLI. Make it feel sharp, fast, and obvious. Wire the sandbox and Ollama packages together into a working tool.

> Read `PROJECT_PLAN.md` first. The CLI surface is defined in §6. The contracts you consume are in §5.1 (sandbox) and §5.2 (Ollama).

---

## Why this matters

You are the integration layer. Ulgac's sandbox and Ibrahim's Ollama wrapper are just libraries until you turn them into a product. You also own the user-facing copy, error messages, and "first 60 seconds" experience — which decides whether anyone uses this twice.

---

## Scope

You own:
- `packages/cli/src/enclave_cli/` — Typer app, REPL, command handlers
- `packages/cli/src/enclave_cli/files/` — file parsers (PDF, Excel, CSV, text)
- `packages/cli/src/enclave_cli/prompts.py` — system prompt template (per PROJECT_PLAN §13.2)
- `packages/cli/src/enclave_cli/sessions.py` — session autosave + resume (§15.1)
- `shared/enclave_core/` — shared `Config`, `EnclaveError` hierarchy (§5.3), logging
- `packages/cli/tests/`
- The `enclave` console script entrypoint
- User-facing strings, error messages, help text, exit-code mapping (§15.2)

You do NOT own:
- How code runs in isolation (Ulgac)
- How models are pulled / queried (Ibrahim)

---

## Deliverables by Milestone

### M0 — Scaffolding
- [ ] `packages/cli/pyproject.toml` declaring `enclave_cli`, console script `enclave = enclave_cli.main:app`.
- [ ] `shared/enclave_core/pyproject.toml`.
- [ ] Typer app skeleton with `enclave --help` working and listing the commands from PROJECT_PLAN §6 (handlers can be stubs).
- [ ] `Config` model and load/save functions in `enclave_core` writing TOML to `~/.enclave/config.toml` (fields per §5.3).
- [ ] `EnclaveError` hierarchy in `enclave_core/errors.py` (§5.3).
- [ ] One smoke test: invoking `enclave --help` in a subprocess returns 0.

### M1 — Walking skeleton
- [ ] `enclave init` creates `~/.enclave/{config.toml,sessions/,log/}` idempotently. **No `work/` dir** — workdir is the user's cwd at runtime (§6).
- [ ] `enclave config show` and `enclave config set <key> <value>` work end-to-end.
- [ ] `enclave models list` calls `enclave_ollama.list_models()` and renders a Rich table.
- [ ] `enclave models use <name>` updates default in config.
- [ ] `enclave ask "hello"` calls `enclave_ollama.generate()` and prints the response.
- [ ] Top-level error handler catches `EnclaveError`, prints `error: <message>`, exits with the code mapped in §15.2.
- [ ] Tests cover: config round-trip, `init` idempotency, `ask` happy path with mocked Ollama, error-class → exit-code mapping.

### M2 — Vertical slice (the actual product)
- [ ] File parsers in `enclave_cli.files`, following parsing rules in §14.2:
  - [ ] `parse_pdf(path) -> str` (pypdf; pdfplumber fallback per page when text is sparse and tables detected)
  - [ ] `parse_excel(path) -> str` (per-sheet markdown tables, header `## Sheet: <name> (rows × cols)`)
  - [ ] `parse_csv(path) -> str` (first 1,000 rows; truncation marker)
  - [ ] `parse_text(path) -> str`
  - [ ] Dispatcher `parse(path)` picks parser by extension; unknown extension raises `CLIError` listing supported types.
- [ ] **File-context limits** (§14.1): max 5 files, 200 KB total extracted text, 100 KB per file. On overflow, truncate with `[... truncated, X KB omitted ...]` marker and warn the user once.
- [ ] **Prompt assembly** (§14.3): system prompt + stable file blocks + history + latest user message. File blocks must remain identical across turns so model providers can prompt-cache them.
- [ ] **System prompt** in `enclave_cli/prompts.py` declares to the model the runtime libraries it may import (per §13.2) and that network is blocked.
- [ ] `enclave ask "..." --file foo.xlsx` ingests files, calls Ollama with assembled prompt.
- [ ] `enclave chat` REPL:
  - [ ] Multi-turn history.
  - [ ] Streaming responses via `enclave_ollama.stream()`; first-token spinner.
  - [ ] Slash commands: `/file`, `/files`, `/model`, `/run`, `/clear`, `/reset`, `/help`, `/exit`.
  - [ ] Key bindings: `Ctrl+C` cancels current model stream and returns to prompt; double `Ctrl+C` exits. `Ctrl+D` exits.
  - [ ] `/run` extracts the most recent `python` code block, displays it in a syntax-highlighted Rich panel, prompts `Run this in sandbox? [y/N]` (skip if `--auto-run` flag or `auto_run=true` in config), then calls `enclave_sandbox.execute_python(code, SandboxPolicy(workdir=Path.cwd(), ...))` and renders stdout/stderr in a labeled panel.
- [ ] **Sessions** (§15.1): autosave to `~/.enclave/sessions/last.json` after every assistant turn; `enclave chat --resume` reloads it; missing files dropped with warning.
- [ ] `enclave run <file.py>` and `enclave run -` (stdin) execute scripts in sandbox at cwd.
- [ ] Tests cover: each parser with a real fixture file, REPL slash command parsing, code block extraction, file-limit truncation, session round-trip, `/run` confirmation flow (both confirm and decline), `--auto-run` skip.

### M3 — Polish
- [ ] No Python tracebacks shown to users by default; `--debug` flag enables tracebacks AND writes operational logs to `~/.enclave/log/enclave.log` (rotated 10 MB × 3). **No conversation content is logged, ever** (§15.3).
- [ ] First-run experience: if `~/.enclave/config.toml` is missing, prompt to run `enclave init`.
- [ ] When `OllamaUnavailableError` is caught, print one clear install/start hint (e.g. `error: Ollama not running. Start it with: ollama serve`).
- [ ] If no default model is set, list models and prompt user to pick.
- [ ] Honor `--no-color` flag and `NO_COLOR` env var for all Rich output.
- [ ] Help text reviewed for every command — examples included.
- [ ] Coverage ≥ 80% for `cli` and `enclave_core`.

---

## Implementation notes

- Typer + Rich. Use `rich.console.Console` for all output so we can mock/capture in tests.
- Keep handlers thin — push logic into testable functions in submodules. Handler bodies should be 5–15 lines.
- File parsing: for Excel, render each sheet as a markdown table and label it. For PDF, prefer `pypdf` for text; fall back to `pdfplumber` only when tables are detected.
- Code-block extraction from model output: regex for ```` ```python ... ``` ```` fences. Test edge cases (nested fences, no language tag, multiple blocks — `/run` always picks the *last* one).
- REPL: use `prompt_toolkit` for line editing + history (better UX than `input()`).
- Config writes are atomic — write to `config.toml.tmp` then `os.replace`.
- Session writes are atomic the same way. Schema lives in `sessions.py` and is versioned (`"version": 1`); add a migration shim if/when the schema changes.
- The system prompt template lives as a single source of truth in `prompts.py`. When sandbox runtime libraries change (PROJECT_PLAN §13.1), update this template in the same PR.
- `SandboxPolicy(workdir=Path.cwd(), ...)` — always pass the user's cwd at invocation time, never a config-stored path.

---

## Testing rules (non-negotiable)

- Every command handler has at least one test that invokes it via `typer.testing.CliRunner`.
- File parsers tested against real fixture files committed under `packages/cli/tests/fixtures/`.
- Mock the Ollama and sandbox packages in CLI unit tests — integration tests in `tests/integration/` exercise the real ones.
- Every PR adds tests for the code it touches. CI blocks merges otherwise.

---

## Interfaces with other members

- **Ulgac (sandbox):** consumer. If you need a new field on `ExecutionResult` or a new policy knob, open a contract-change PR and ping him.
- **Ibrahim (Ollama):** consumer. Same rule for `enclave_ollama.api`. You'll be the one most affected by streaming UX, so push for clarity early.

---

## What "done for v0.1" looks like

The full PROJECT_PLAN §12.1 first-run transcript runs end-to-end with no surprises. At no point does any data leave the machine, and the model's code can't read anything outside the cwd it was invoked from. Ctrl+C is responsive. Errors are one-line. Resume works.
