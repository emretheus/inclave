"""Windows isolation backend for inclave-sandbox.

This is the Windows counterpart to ``executor.py`` (macOS / Seatbelt). It honors
the same SandboxPolicy contract and returns the same ExecutionResult, but the
isolation primitives differ:

  - macOS rlimits (``resource.setrlimit``)  ->  Windows **Job Objects**
    (memory cap, active-process cap, kill-on-job-close).
  - macOS ``os.killpg`` on timeout          ->  ``TerminateJobObject`` (kills the
    whole process tree atomically).
  - macOS Seatbelt deny-by-default profile   ->  (no direct equivalent at this
    isolation tier — see the parity note below).

Isolation tier (v1): this backend provides resource isolation (CPU/memory/
process-count/fork-bomb/timeout) plus a minimal environment and workdir-as-cwd.
It does **not** provide Seatbelt-grade filesystem deny-by-default. A stronger
tier (Windows AppContainer: capability SIDs + restricted token) is deferred to
a future version. See packages/sandbox/README.md for the honest parity table.
This module is imported lazily from api.py only on win32, so the ctypes/windll
references below are never evaluated on other platforms.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

from inclave_sandbox.api import ExecutionResult, SandboxPolicy
from inclave_sandbox.errors import SandboxError
from inclave_sandbox.runtime import runtime_python

MAX_OUTPUT_FILE_BYTES = 100 * 1024 * 1024  # 100 MB (parity with macOS backend)

# --- Win32 constants -------------------------------------------------------
CREATE_SUSPENDED = 0x00000004
CREATE_NEW_PROCESS_GROUP = 0x00000200
PROCESS_ALL_ACCESS = 0x1F0FFF

# JOBOBJECT_BASIC_LIMIT_INFORMATION.LimitFlags
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_LIMIT_PROCESS_TIME = 0x00000002

# SetInformationJobObject class
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def _kernel32() -> ctypes.WinDLL:
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _build_env(workdir: Path) -> dict[str, str]:
    """Return a minimal, predictable environment for the jailed process.

    Windows counterpart to the macOS ``_build_env``. We keep SystemRoot (dyld
    equivalent: the loader needs it to find system DLLs) and point all temp/home
    paths at the workdir so stray writes land inside the jail. PATH is scoped to
    the runtime interpreter's directory only.
    """
    py_dir = str(runtime_python().parent)
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    return {
        "SystemRoot": system_root,
        "PATH": f"{py_dir};{system_root}\\System32",
        "HOME": str(workdir),
        "USERPROFILE": str(workdir),
        "TEMP": str(workdir),
        "TMP": str(workdir),
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
    }


def _validate(policy: SandboxPolicy) -> None:
    """Mirror the macOS backend's policy validation contract."""
    if not policy.workdir.is_absolute():
        raise SandboxError(f"policy.workdir must be absolute, got {policy.workdir!r}")
    if not policy.workdir.is_dir():
        raise SandboxError(f"policy.workdir does not exist: {policy.workdir}")
    if policy.allow_network:
        raise SandboxError("allow_network=True is not supported in v0.1")
    # Surfaces the same build hint as macOS if the runtime venv is missing.
    runtime_python()


def _create_job(policy: SandboxPolicy) -> wintypes.HANDLE:
    """Create a Job Object enforcing memory, process-count, and kill-on-close.

    This is the Windows analogue of the macOS ``setrlimit`` preexec hook:
      - ProcessMemoryLimit  ~= RLIMIT_AS / RLIMIT_DATA
      - ActiveProcessLimit=1 ~= fork-bomb protection (RLIMIT_NPROC-ish)
      - KILL_ON_JOB_CLOSE   ~= os.killpg cleanup — closing our handle (even on
        crash) tears down the whole tree.
      - PerJobUserTimeLimit ~= RLIMIT_CPU (best-effort; wall-clock kill below is
        the hard stop).
    """
    k32 = _kernel32()
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    job = k32.CreateJobObjectW(None, None)
    if not job:
        raise SandboxError(f"CreateJobObject failed (err={ctypes.get_last_error()})")

    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    basic = info.BasicLimitInformation
    basic.LimitFlags = (
        JOB_OBJECT_LIMIT_PROCESS_MEMORY
        | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        | JOB_OBJECT_LIMIT_PROCESS_TIME
    )
    basic.ActiveProcessLimit = 1
    # CPU time limit is expressed in 100-nanosecond ticks.
    basic.PerProcessUserTimeLimit = policy.cpu_seconds * 10_000_000
    info.BasicLimitInformation = basic
    info.ProcessMemoryLimit = policy.memory_mb * 1024 * 1024

    ok = k32.SetInformationJobObject(
        job,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not ok:
        err = ctypes.get_last_error()
        k32.CloseHandle(job)
        raise SandboxError(f"SetInformationJobObject failed (err={err})")
    return job


def _assign_to_job(job: wintypes.HANDLE, pid: int) -> None:
    """Open the suspended child and attach it to the job before it runs.

    Order matters: the child is started suspended, assigned here, then resumed —
    so it cannot spawn descendants or allocate before the limits apply.
    """
    k32 = _kernel32()
    k32.OpenProcess.restype = wintypes.HANDLE
    handle = k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not handle:
        raise SandboxError(f"OpenProcess failed (err={ctypes.get_last_error()})")
    try:
        if not k32.AssignProcessToJobObject(job, handle):
            raise SandboxError(
                f"AssignProcessToJobObject failed (err={ctypes.get_last_error()})"
            )
    finally:
        k32.CloseHandle(handle)


def _run(cmd: list[str], *, policy: SandboxPolicy) -> ExecutionResult:
    env = _build_env(policy.workdir)
    started = time.monotonic()
    timed_out = False
    k32 = _kernel32()

    job = _create_job(policy)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(policy.workdir),
            creationflags=CREATE_SUSPENDED | CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        # Attach to the job while suspended, then let it run.
        try:
            _assign_to_job(job, proc.pid)
        except SandboxError:
            proc.kill()
            raise
        _resume_process(proc.pid)

        try:
            stdout_b, stderr_b = proc.communicate(timeout=policy.wall_clock_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            # TerminateJobObject kills the whole tree atomically (killpg analogue).
            k32.TerminateJobObject(job, 1)
            stdout_b, stderr_b = proc.communicate()
    finally:
        # KILL_ON_JOB_CLOSE guarantees no survivors once the handle is gone.
        k32.CloseHandle(job)

    duration_ms = int((time.monotonic() - started) * 1000)
    return ExecutionResult(
        stdout=stdout_b.decode("utf-8", errors="replace"),
        stderr=stderr_b.decode("utf-8", errors="replace"),
        exit_code=proc.returncode if not timed_out else -1,
        timed_out=timed_out,
        duration_ms=duration_ms,
    )


def _resume_process(pid: int) -> None:
    """Resume every thread of a CREATE_SUSPENDED process.

    A freshly created suspended process has exactly one thread; we enumerate via
    a thread snapshot and resume any belonging to our pid to be robust.
    """
    TH32CS_SNAPTHREAD = 0x00000004
    THREAD_SUSPEND_RESUME = 0x0002

    class THREADENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG),
            ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        ]

    k32 = _kernel32()
    snapshot = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        raise SandboxError(f"CreateToolhelp32Snapshot failed (err={ctypes.get_last_error()})")
    try:
        entry = THREADENTRY32()
        entry.dwSize = ctypes.sizeof(THREADENTRY32)
        if not k32.Thread32First(snapshot, ctypes.byref(entry)):
            raise SandboxError("Thread32First failed; could not resume sandboxed process")
        while True:
            if entry.th32OwnerProcessID == pid:
                k32.OpenThread.restype = wintypes.HANDLE
                thread = k32.OpenThread(THREAD_SUSPEND_RESUME, False, entry.th32ThreadID)
                if thread:
                    k32.ResumeThread(thread)
                    k32.CloseHandle(thread)
            if not k32.Thread32Next(snapshot, ctypes.byref(entry)):
                break
    finally:
        k32.CloseHandle(snapshot)


def execute_python_impl(code: str, policy: SandboxPolicy) -> ExecutionResult:
    """Concrete Windows implementation. Public entry is inclave_sandbox.api.execute_python."""
    _validate(policy)
    py = runtime_python()
    cmd = [
        str(py),
        "-I",  # isolated mode: ignore PYTHON* env vars and user site-packages
        "-c",
        code,
    ]
    return _run(cmd, policy=policy)
