# inclave-sandbox

Isolated code execution for inclave. Lets the CLI hand model-generated
Python (or shell) to a jailed process that cannot escape the user's working
directory or reach the network.

> **Status:** M0 scaffolding. Public API is stubbed and raises
> `NotImplementedError`. Real isolation lands in M1.

## Threat model (plain English)

We assume:

1. The model is **untrusted**. It can produce wrong, careless, or actively
   adversarial code.
2. The user is **trusted**. They invoked the CLI and want code to run.
3. The host OS install is **trusted**. Kernel-level escapes are out of scope.

We try to prevent:

- Reading any file outside the user's current working directory (no
  `~/.ssh/id_rsa`, no `~/.aws/credentials`, no Keychain).
- Writing any file outside the working directory.
- Any network access — DNS, TCP, UDP, Unix sockets to system services.
- Resource exhaustion: CPU runaway, fork bombs, memory blow-ups.
- Long-running hangs — every execution has a wall-clock kill.
- Inheriting environment variables that could leak secrets or alter behavior.

We do **not** try to prevent:

- Side-channel attacks (timing, cache).
- Kernel exploits.
- Hardware-level attacks.
- Anything the user explicitly opts into via a future `--allow-network` flag.

## Platforms

`execute_python` picks an isolation backend per platform (`api.py`, on
`sys.platform`). Both backends honor the same `SandboxPolicy` and return the
same `ExecutionResult`; callers (CLI and the desktop bridge) never branch on OS.

| Guarantee | macOS (Seatbelt) | Windows (Job Objects) |
|---|---|---|
| CPU / memory limit | ✅ `setrlimit` | ✅ Job Object limits |
| Process count / fork-bomb | ✅ rlimit | ✅ `ActiveProcessLimit=1` |
| Wall-clock kill (whole tree) | ✅ `killpg` | ✅ `TerminateJobObject` |
| Minimal environment | ✅ | ✅ |
| Network deny | ✅ (Seatbelt `deny network*`) | ⚠️ env-only, **not enforced** |
| Filesystem deny-by-default | ✅ (Seatbelt profile) | ❌ **not at this tier** |

**Windows is a weaker tier on filesystem and network isolation.** It enforces
resource limits and runs in the workdir with a minimal environment, but it does
**not** deny reads/writes outside the workdir the way the Seatbelt profile does,
and network is only discouraged via the environment, not blocked. A stronger
Windows tier (AppContainer: capability SIDs + restricted token, and a network
firewall rule) is deferred to a future version. Treat the Windows backend as
resource isolation + defense-in-depth, **not** a filesystem/network seal.

## How it works (macOS)

1. The CLI calls `execute_python(code, SandboxPolicy(workdir=Path.cwd(), ...))`.
2. We render a Seatbelt profile (`profiles/default.sb`) substituting the
   working directory into the `(allow file-* (subpath ...))` rules.
3. We `subprocess.Popen(["sandbox-exec", "-f", profile, RUNTIME_PYTHON, "-c", code], ...)`.
4. A `preexec_fn` applies `setrlimit` for CPU, address space, file size,
   and open files.
5. Environment is wiped to a minimal `PATH=/usr/bin:/bin` and `HOME=workdir`.
6. We watch the process — kill the whole process group on wall-clock timeout.
7. Result returned as `ExecutionResult` (stdout, stderr, exit code, timed_out,
   duration).

## How it works (Windows)

1. Same `execute_python` entry point; `api.py` dispatches to
   `executor_windows.py`.
2. We create a **Job Object** with a process-memory cap, `ActiveProcessLimit=1`
   (fork-bomb protection), a per-process CPU-time limit, and
   `KILL_ON_JOB_CLOSE` (closing our handle, even on crash, tears down the tree).
3. We launch the bundled interpreter `CREATE_SUSPENDED`, assign it to the job
   **before** it runs, then resume it — so limits apply before any work starts.
4. Environment is minimized (`PATH` scoped to the interpreter dir + System32,
   `HOME`/`TEMP`/`TMP` pointed at the workdir).
5. On wall-clock timeout we call `TerminateJobObject`, killing the whole tree.
6. Same `ExecutionResult` shape is returned.

Uses only the standard library (`ctypes`) — no `pywin32` dependency.

The bundled Python runtime lives at `runtime/` (built per machine via
`uv lock`). It contains a frozen set of libraries: pandas, numpy, openpyxl,
pypdf, matplotlib. The exact list is in `runtime/pyproject.toml`.

## Known limitations

- **Seatbelt is deprecated by Apple.** It still works on every shipped macOS
  but Apple may remove it. We accept this risk for v0.1.
- **`sandbox-exec` denials are coarse.** Parsing the deny log to surface
  *what* was blocked is best-effort.
- **Resource limits via `setrlimit` are not airtight.** A determined attacker
  with code execution can sometimes side-step limits via syscalls. The
  combination with Seatbelt narrows this significantly but doesn't eliminate it.
- **The macOS App Sandbox would be stronger** but requires entitlements and
  Developer ID signing, which we deferred for v0.1.
- **The Windows backend does not isolate the filesystem or network** at this
  tier (see the Platforms table). AppContainer + a firewall rule would close
  this gap and are deferred to a future version.

When in doubt, treat this sandbox as defense-in-depth, not a hermetic seal.

## Public API

```python
from inclave_sandbox import (
    SandboxPolicy, ExecutionResult, SandboxError,
    execute_python, execute_shell,
)
```

See `src/inclave_sandbox/api.py` for full signatures.

## Tests

```
uv run pytest packages/sandbox
```

Backend tests are platform-gated: `test_executor.py` runs only on macOS,
`test_executor_windows.py` only on Windows; each skips elsewhere with a clear
reason. `test_dispatch.py` runs everywhere and covers the `api.py` platform
routing.

The Windows backend can only be exercised on a real Windows host (macOS/Linux CI
skips it). See [`WINDOWS_TESTING.md`](WINDOWS_TESTING.md) for the setup and the
manual checklist to validate it.
