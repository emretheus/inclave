# Testing the Windows sandbox backend

The Windows isolation backend (`executor_windows.py`, Job Objects via `ctypes`)
can only be exercised on a real Windows host. macOS/Linux CI **skips** every
`test_executor_windows.py` case, so a green run on those platforms says nothing
about whether the Windows path actually works. This document is the manual
checklist to run on Windows before trusting it.

> Why manual? The Job Object syscalls (`CreateJobObjectW`,
> `AssignProcessToJobObject`, `TerminateJobObject`) and the
> `CREATE_SUSPENDED → assign → resume` launch dance only execute on Windows.
> There is no way to validate them from a Mac.

## Prerequisites

- **Windows 10 / 11** (or Windows Server 2019+). No admin rights required —
  Job Objects work for an unprivileged user.
- **Python 3.12 or 3.13** on `PATH` (`python --version`).
- **uv** — install with:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **git**, and a clone of this repo on the `feat/windows-sandbox-support` branch.

No `pywin32` or other extra dependency is needed — the backend uses only the
standard library.

## One-time setup

From the repo root, in **PowerShell**:

```powershell
# 1. Sync the dev environment (test deps, the workspace packages).
uv sync

# 2. Build the bundled runtime venv the sandbox executes against.
#    On Windows this produces .venv\Scripts\python.exe (runtime.py finds it).
cd packages\sandbox\runtime
uv sync
cd ..\..\..
```

If step 2 is skipped, the Windows tests skip themselves with the reason
`runtime venv not built` (same guard as macOS).

## Run the test suite

```powershell
uv run pytest packages\sandbox -v
```

**Expected on Windows:**

- `test_executor_windows.py` — all cases **run and pass** (these skip on macOS).
- `test_dispatch.py` — runs everywhere; passes.
- `test_executor.py` — **skipped** (`requires macOS`). This is correct.

If you see `test_executor_windows.py` reported as *skipped*, the runtime venv
isn't built — redo setup step 2.

## What each Windows test proves

| Test | What it verifies |
|---|---|
| `test_hello_world` | Backend launches the bundled interpreter and captures stdout. |
| `test_non_zero_exit` | Exit codes propagate. |
| `test_stderr_capture` | stderr is captured separately. |
| `test_wall_clock_timeout` | `TerminateJobObject` kills a `sleep(30)` at the 2s wall-clock limit; `timed_out=True`. |
| `test_workdir_writable` / `test_workdir_readable` | cwd is the workdir; reads/writes there work. |
| `test_env_is_minimal` | Host identity (`USERNAME`) is not leaked; `HOME`/`PATH` present. |
| `test_fork_bomb_is_capped` | `ActiveProcessLimit=1` blocks the child from spawning a second process. |
| `test_validate_rejects_*` | Policy validation (absolute/existing workdir, `allow_network` rejected) matches macOS. |

## Manual smoke checks (optional but recommended)

These exercise behavior the unit tests assert, but by hand so you can watch it.

### 1. Basic execution

```powershell
uv run python -c "import inclave_sandbox as sb; from pathlib import Path; r = sb.execute_python('print(2+2)', sb.SandboxPolicy(workdir=Path.cwd())); print(repr(r.stdout), r.exit_code, r.timed_out)"
```
Expect: `'4\n' 0 False`.

### 2. Wall-clock kill (whole tree dies)

```powershell
uv run python -c "import inclave_sandbox as sb; from pathlib import Path; r = sb.execute_python('import time; time.sleep(30)', sb.SandboxPolicy(workdir=Path.cwd(), wall_clock_seconds=2)); print('timed_out=', r.timed_out)"
```
Expect: `timed_out= True`, and the command returns after ~2s (not 30s). In Task
Manager, no orphaned `python.exe` should survive — `KILL_ON_JOB_CLOSE` plus
`TerminateJobObject` tears the tree down.

### 3. Memory cap

```powershell
uv run python -c "import inclave_sandbox as sb; from pathlib import Path; r = sb.execute_python('x = bytearray(2_000_000_000)', sb.SandboxPolicy(workdir=Path.cwd(), memory_mb=256)); print('exit=', r.exit_code)"
```
Expect: a **non-zero** exit (`MemoryError` inside the jail) — the 256 MB Job
Object `ProcessMemoryLimit` denies the ~2 GB allocation.

### 4. Fork-bomb / process cap

```powershell
uv run python -c "import inclave_sandbox as sb; from pathlib import Path; r = sb.execute_python('import subprocess,sys; subprocess.Popen([sys.executable,\"-c\",\"pass\"])', sb.SandboxPolicy(workdir=Path.cwd())); print('exit=', r.exit_code)"
```
Expect: **non-zero** exit — `ActiveProcessLimit=1` prevents the second process.

## Known limitations to keep in mind while testing

This backend is **resource isolation + defense-in-depth**, not a filesystem or
network seal (see `README.md` → Platforms). The following are *expected* to NOT
be blocked at this tier — do not file them as bugs:

- Reading/writing files **outside** the workdir (no Seatbelt-equivalent FS deny).
- Network access (only discouraged via a minimal environment, not firewalled).

These gaps are the planned AppContainer (v2) work.

## Reporting results

When you've run the above on Windows, note in the PR:

- Windows version (`winver`) and Python version.
- `pytest packages\sandbox -v` summary line (passed/skipped counts).
- Any smoke check that behaved differently than "Expect:" above.
