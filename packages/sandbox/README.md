# enclave-sandbox

Isolated code execution for enclave-code. Lets the CLI hand model-generated
Python (or shell) to a jailed process that cannot escape the user's working
directory or reach the network.

> **Status:** M0 scaffolding. Public API is stubbed and raises
> `NotImplementedError`. Real isolation lands in M1.

## Threat model (plain English)

We assume:

1. The model is **untrusted**. It can produce wrong, careless, or actively
   adversarial code.
2. The user is **trusted**. They invoked the CLI and want code to run.
3. The host macOS install is **trusted**. Kernel-level escapes are out of scope.

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

## How it works

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

The bundled Python runtime lives at `runtime/` (built per machine via
`uv lock`). It contains a frozen set of libraries: pandas, numpy, openpyxl,
pypdf, matplotlib. See .github/internal/PROJECT_PLAN.md §13 for the full list.

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

When in doubt, treat this sandbox as defense-in-depth, not a hermetic seal.

## Public API

```python
from enclave_sandbox import (
    SandboxPolicy, ExecutionResult, SandboxError,
    execute_python, execute_shell,
)
```

See `src/enclave_sandbox/api.py` for full signatures.

## Tests

```
uv run pytest packages/sandbox
```

Adversarial tests (M2+) require macOS — they're skipped on other platforms
with a clear reason.
