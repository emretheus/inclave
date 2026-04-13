# Tasks — Ulgac (Sandbox / Isolated Code Execution)

**Package:** `packages/sandbox` — `enclave_sandbox`
**Goal:** Provide a safe way to execute model-generated code on the user's Mac without it being able to read private files, hit the network, or burn the machine down.

> Read `PROJECT_PLAN.md` first. The frozen API contract you must implement is in §5.1.

---

## Why this matters

The whole product premise — "let the model write and run code on your files" — is only acceptable if the code physically cannot escape. If your sandbox leaks, the project's value proposition collapses. **This is the security-critical package.** Treat every "it works" moment with suspicion until adversarial tests pass.

---

## Scope

You own:
- `packages/sandbox/src/enclave_sandbox/` — implementation
- `packages/sandbox/profiles/*.sb` — Seatbelt profile templates
- `packages/sandbox/runtime/` — frozen `uv`-managed Python venv used inside the jail (PROJECT_PLAN §13)
- `packages/sandbox/tests/` — including adversarial suite
- The `SandboxError` exception class (subclass of `enclave_core.errors.EnclaveError`)
- Documentation of the threat model, known limitations, and bundled runtime libraries

You do NOT own:
- How code reaches you (CLI's job)
- What the code does (model's job)
- Where output is shown (CLI's job)

---

## Deliverables by Milestone

### M0 — Scaffolding
- [ ] Package skeleton with `pyproject.toml` declaring `enclave_sandbox`.
- [ ] Stub `api.py` exporting the types and functions in PROJECT_PLAN §5.1 (raise `NotImplementedError`).
- [ ] `SandboxError(EnclaveError)` defined and exported.
- [ ] One smoke test that imports the package and calls a stub.
- [ ] README in `packages/sandbox/README.md` describing the threat model in plain English.

### M1 — Walking skeleton
- [ ] `execute_python(code, policy)` works for trivial code: returns stdout, exit code, duration.
- [ ] Default Seatbelt profile (`profiles/default.sb`) committed and loaded by the executor; `(workdir)` substituted from `policy.workdir` at call time (which the CLI sets to user's cwd — never assume a fixed path).
- [ ] `setrlimit` wired up: CPU time, address space, file size, open files.
- [ ] Wall-clock kill via `subprocess` + `signal.SIGKILL` after `wall_clock_seconds`.
- [ ] **Curated runtime venv** at `packages/sandbox/runtime/`, locked via `uv lock`. Bundled libs per PROJECT_PLAN §13.1: `pandas`, `numpy`, `openpyxl`, `pypdf`, `matplotlib` (Agg backend). The Seatbelt jail invokes `runtime/bin/python3`, not system Python.
- [ ] Tests: happy path (`print("hi")`), timeout, non-zero exit, captured stderr, `import pandas` works inside the jail.

### M2 — Adversarial hardening
- [ ] Implement `execute_shell(command, policy)` (same policy semantics, runs `/bin/sh -c`).
- [ ] Adversarial test suite — every one of these MUST pass:
  - [ ] Read `~/.ssh/id_rsa` → blocked (file-read denied).
  - [ ] Read `/etc/hosts` → blocked (or only if explicitly in profile).
  - [ ] `socket.connect(('1.1.1.1', 80))` → blocked (network denied).
  - [ ] `urllib.request.urlopen('https://example.com')` → blocked.
  - [ ] `os.fork()` loop → killed by rlimit / wall-clock.
  - [ ] Allocate 2 GB list → killed by memory rlimit.
  - [ ] Write to `/tmp/escape.txt` → blocked.
  - [ ] Write to `<workdir>/output.csv` → succeeds.
  - [ ] Read `<workdir>/input.xlsx` → succeeds.
  - [ ] `os.execv("/bin/bash", ...)` → still inside sandbox (child inherits profile).
- [ ] Runtime tests: every bundled library imports cleanly inside the jail and a representative one-liner per library executes (`pd.DataFrame(...)`, `np.array(...)`, `openpyxl.load_workbook(...)`, `pypdf.PdfReader(...)`, `plt.savefig(...)` to workdir).
- [ ] Document one known-limitation per limitation in README (be honest — Seatbelt is not perfect).

### M3 — Polish
- [ ] Useful error messages: when a sandbox violation occurs, the `ExecutionResult.stderr` should hint at *what* was blocked (parse `sandbox-exec` deny logs).
- [ ] Performance: cold-start of sandboxed Python `< 500ms` on M-series Mac.
- [ ] Coverage ≥ 90% for this package (enforced in CI).

---

## Implementation notes

- Use `subprocess.Popen(["sandbox-exec", "-f", profile_path, str(RUNTIME_PYTHON), "-c", code], ...)` where `RUNTIME_PYTHON` is the bundled `runtime/bin/python3`.
- Render the profile from a template — `(workdir)` should be substituted to the absolute path from `policy.workdir` so the profile authorizes only that directory. The Seatbelt profile must also allow read of `runtime/` so the bundled Python can load its stdlib and site-packages.
- Apply `setrlimit` in a `preexec_fn` so it's set before `exec`.
- Always run with a fresh empty `env` (only `PATH=/usr/bin:/bin` and `HOME=<workdir>`). Inherited env vars are an injection vector.
- Never use `shell=True` for the outer call. Inner `execute_shell` is fine because the inner shell is itself jailed.
- Resource cleanup: kill the whole process group on timeout (`os.killpg`).
- Adding to the runtime library list is a deliberate decision: it requires updating §13.1 in PROJECT_PLAN, the runtime lock file, and the system prompt template in `enclave_cli/prompts.py` (Emre owns that file) — all in the same PR.

---

## Testing rules (non-negotiable)

- Every public function has unit tests.
- Every adversarial scenario in M2 lives as a single named test (`test_blocks_ssh_key_read`, etc.) so a regression names itself.
- Tests run on `macos-latest` in CI. Skip with a clear reason on Linux dev machines.
- A new "thing the sandbox should block" goes in as a failing test first, then the fix.

---

## Interfaces with other members

- **Emre (CLI):** consumes your `execute_python` / `execute_shell`. If you need to change `SandboxPolicy` or `ExecutionResult`, open a contract-change PR and ping him before merging.
- **Ibrahim (Ollama):** no direct dependency. The model produces code, the CLI hands it to you.

---

## What "done for v0.1" looks like

A user types `/run` in `enclave chat`, the CLI hands the model's last Python block to your `execute_python` with `policy.workdir = Path.cwd()`, and one of two things happens:
1. The code runs in a jail where it can only see the user's current working directory, can't reach the network, can't fork-bomb, can `import pandas/numpy/openpyxl/pypdf/matplotlib`, and finishes in < 30s — output is returned.
2. The code violates the policy and is killed with a clear `stderr` message — the user sees what was blocked.

No third outcome.
