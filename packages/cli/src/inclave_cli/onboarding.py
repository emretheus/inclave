"""First-run onboarding — make the CLI itself the only guide.

The goal is that `inclave` (bare) just works:

  - lazy-creates ~/.inclave/ on first run
  - if Ollama isn't running, offers to start it
  - if no models are installed, offers to pull a recommended one
  - if no default is set, asks which installed model to use

Each helper is interactive when stdin is a TTY and raises a clean error
when it isn't (so pipes / CI / `inclave ask` stay deterministic).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

import httpx
from inclave_core import (
    OllamaUnavailableError,
    enclave_dir,
    load_config,
    log_dir,
    sessions_dir,
    set_config_value,
)
from rich.console import Console

OLLAMA_URL = "http://127.0.0.1:11434/api/tags"

# Curated first-time picks. Sizes are approximate (Ollama reports exact bytes
# on pull). Keep this list short — choice fatigue is the enemy.
RECOMMENDED_MODELS: list[tuple[str, str, str]] = [
    ("llama3.2", "2.0 GB", "fast, great default"),
    ("llama3.1:8b", "4.7 GB", "bigger, slower, better reasoning"),
    ("qwen2.5-coder:7b", "4.4 GB", "coding-tuned"),
]


def _is_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def ensure_dirs() -> None:
    """Idempotently create ~/.inclave/{sessions,log,workspaces}."""
    enclave_dir()
    sessions_dir()
    log_dir()


def _ollama_up(timeout: float = 1.0) -> bool:
    try:
        httpx.get(OLLAMA_URL, timeout=timeout)
        return True
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError):
        return False


def _ollama_installed() -> bool:
    from shutil import which

    return which("ollama") is not None


def _wait_for_ollama(console: Console, timeout: float = 15.0) -> bool:
    """Poll ollama up to `timeout` seconds, printing a single live status."""
    deadline = time.monotonic() + timeout
    with console.status("[dim]waiting for ollama on 127.0.0.1:11434…[/dim]"):
        while time.monotonic() < deadline:
            if _ollama_up(timeout=0.5):
                return True
            time.sleep(0.5)
    return False


def _spawn_ollama_daemon() -> None:
    """Start `ollama serve` detached so it survives this process exiting."""
    # stdout/stderr -> /dev/null so we don't pipe daemon output into the REPL.
    devnull = subprocess.DEVNULL
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=devnull,
        stderr=devnull,
        stdin=devnull,
        start_new_session=True,
        env={**os.environ},
    )


def ensure_ollama_running(console: Console, err_console: Console) -> None:
    """Walk the user through getting Ollama up. Raises if we can't continue."""
    if _ollama_up():
        return

    if not _is_tty():
        raise OllamaUnavailableError("Ollama is not running. Start it with: ollama serve")

    if not _ollama_installed():
        err_console.print("[yellow]![/yellow] ollama isn't installed.")
        err_console.print("    install with: [bold]brew install ollama[/bold]")
        err_console.print("    then re-run [bold]inclave[/bold] — i'll start it for you.")
        raise OllamaUnavailableError("ollama not installed")

    console.print()
    console.print("[yellow]![/yellow] ollama isn't running.")
    console.print()
    console.print("  1) [bold]start it for me[/bold]   [dim](recommended)[/dim]")
    console.print("  2) i'll start it myself  [dim](i'll wait up to 15s)[/dim]")
    console.print("  q) quit")
    console.print()
    choice = console.input("  > ").strip().lower()

    if choice in ("q", "quit", "exit"):
        raise OllamaUnavailableError("ollama not started")

    if choice in ("", "1"):
        console.print("[dim]starting ollama in the background…[/dim]")
        _spawn_ollama_daemon()
        if _wait_for_ollama(console, timeout=20.0):
            console.print("[green]✓[/green] ollama up")
            return
        raise OllamaUnavailableError("ollama didn't come up. start it manually: ollama serve")

    if choice == "2":
        if _wait_for_ollama(console, timeout=15.0):
            console.print("[green]✓[/green] ollama up")
            return
        raise OllamaUnavailableError("ollama didn't come up. start it manually: ollama serve")

    raise OllamaUnavailableError(f"unrecognized choice: {choice!r}")


def _print_recommended_models(console: Console) -> None:
    console.print()
    console.print("[yellow]![/yellow] no models installed.")
    console.print("  pick one to pull (runs offline once downloaded):")
    console.print()
    for i, (name, size, blurb) in enumerate(RECOMMENDED_MODELS, 1):
        marker = "[bold]" if i == 1 else ""
        endm = "[/bold]" if i == 1 else ""
        console.print(f"  {i}) {marker}{name}{endm}  [dim]{size}  · {blurb}[/dim]")
    console.print(f"  {len(RECOMMENDED_MODELS) + 1}) other…  [dim](type a model name)[/dim]")
    console.print("  q) quit")
    console.print()


def _pull_and_default(name: str, console: Console) -> None:
    """Pull a model and set it as the default. Streams progress to the console."""
    from inclave_ollama.api import pull_model

    console.print(f"[dim]pulling {name}…[/dim]")
    last = ""
    for line in pull_model(name):
        if line and line != last:
            console.print(f"  [dim]{line}[/dim]")
            last = line
    set_config_value("default_model", name)
    console.print(f"[green]✓[/green] pulled {name} · set as default")


def _prompt_install_model(console: Console, err_console: Console) -> str:
    """Interactive picker. Returns the chosen model name; raises if cancelled."""
    _print_recommended_models(console)
    choice = console.input("  > ").strip().lower()

    if choice in ("q", "quit", "exit"):
        raise OllamaUnavailableError("no model selected")

    if choice in ("", "1"):
        name = RECOMMENDED_MODELS[0][0]
    elif choice.isdigit() and 1 <= int(choice) <= len(RECOMMENDED_MODELS):
        name = RECOMMENDED_MODELS[int(choice) - 1][0]
    elif choice == str(len(RECOMMENDED_MODELS) + 1) or choice == "other":
        name = console.input("  model name: ").strip()
        if not name:
            raise OllamaUnavailableError("no model name given")
    else:
        # Treat free text as a direct model name (so users can paste from Ollama
        # site without re-numbering).
        name = choice

    _pull_and_default(name, console)
    return name


def _prompt_pick_existing(console: Console, names: list[str], current: str | None) -> str:
    """Ask the user to pick from already-installed models. Returns the name."""
    console.print()
    if current:
        console.print(f"[yellow]![/yellow] current default ({current}) is gone.")
    else:
        console.print("[yellow]![/yellow] no default model set.")
    console.print("  pick a default from your installed models:")
    console.print()
    for i, name in enumerate(names, 1):
        marker = "[bold]" if i == 1 else ""
        endm = "[/bold]" if i == 1 else ""
        console.print(f"  {i}) {marker}{name}{endm}")
    console.print("  q) quit")
    console.print()
    choice = console.input("  > ").strip().lower()
    if choice in ("q", "quit", "exit"):
        raise OllamaUnavailableError("no default model chosen")
    if choice in ("", "1"):
        return names[0]
    if choice.isdigit() and 1 <= int(choice) <= len(names):
        return names[int(choice) - 1]
    # Free text — accept if it matches.
    if choice in names:
        return choice
    raise OllamaUnavailableError(f"unrecognized choice: {choice!r}")


def ensure_default_model(
    console: Console,
    err_console: Console,
    *,
    list_models_fn: Callable[..., list[Any]] | None = None,
) -> str:
    """Return a usable model name. Pull/select as needed.

    The list_models_fn parameter is for test injection — production callers
    pass nothing and get inclave_ollama.api.list_models.
    """
    if list_models_fn is None:
        from inclave_ollama.api import list_models as _lm

        list_models_fn = _lm

    cfg = load_config()
    installed = list_models_fn()
    names = [m.name for m in installed]

    # Happy path: default is set and still installed.
    if cfg.default_model and cfg.default_model in names:
        return str(cfg.default_model)

    if not _is_tty():
        # Non-interactive: error out cleanly so pipelines fail loud, not hang.
        if not names:
            raise OllamaUnavailableError("no models installed. pull one with: ollama pull llama3.2")
        raise OllamaUnavailableError("no default model. set one with: inclave models use <name>")

    if not names:
        name = _prompt_install_model(console, err_console)
        return name

    # Models exist but no/invalid default.
    name = _prompt_pick_existing(console, names, cfg.default_model)
    set_config_value("default_model", name)
    console.print(f"[green]✓[/green] default model: {name}")
    return name


def preflight(console: Console, err_console: Console) -> str:
    """Run all checks in order; return a model name ready to chat with."""
    ensure_dirs()
    ensure_ollama_running(console, err_console)
    return ensure_default_model(console, err_console)
