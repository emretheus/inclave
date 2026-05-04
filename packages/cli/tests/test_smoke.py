"""Smoke tests for the inclave CLI — verify the console script is installed and runs.

These tests invoke the real `inclave` binary via subprocess to catch packaging
regressions that unit tests would miss (missing entry point, import-time errors, etc.).
"""

from __future__ import annotations

import subprocess
import sys


def test_inclave_help_exits_zero() -> None:
    """`inclave --help` must exit 0 and list the top-level commands."""
    result = subprocess.run(
        ["inclave", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"inclave --help returned {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    for command in ("init", "config", "models", "chat", "ask", "run"):
        assert command in result.stdout, f"missing command in help: {command}"


def test_inclave_module_invocation_exits_zero() -> None:
    """`python -m inclave_cli.main --help` must also work (fallback if console script missing)."""
    result = subprocess.run(
        [sys.executable, "-m", "inclave_cli.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"module invocation returned {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
