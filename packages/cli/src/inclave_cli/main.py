"""InClave CLI entrypoint.

Defines the `enclave` command and its subcommands per PROJECT_PLAN.md §6.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from inclave_core import (
    CLIError,
    InClaveError,
    OllamaUnavailableError,
    add_file,
    clear_workspace,
    enclave_dir,
    get_logger,
    list_files,
    list_sessions,
    load_config,
    log_dir,
    remove_file,
    sessions_dir,
    set_config_value,
    setup_logging,
)
from inclave_core.config import CONFIG_KEYS
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Consoles are rebuilt by the top-level callback when --no-color is passed.
console = Console()
err_console = Console(stderr=True)
log = get_logger()

EXIT_OK = 0
EXIT_USER = 1
EXIT_CONFIG = 2
EXIT_OLLAMA_UNAVAILABLE = 3
EXIT_SANDBOX = 4
EXIT_INTERNAL = 99

app = typer.Typer(
    name="inclave",
    help="Local-first, privacy-preserving CLI for macOS — sandbox + Ollama + file work.",
    # Bare `inclave` (no subcommand) runs chat with onboarding. Subcommand groups
    # below still default to printing their own help when invoked without args.
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)

config_app = typer.Typer(help="Manage InClave configuration.", no_args_is_help=True)
models_app = typer.Typer(help="Manage local Ollama models.", no_args_is_help=True)
files_app = typer.Typer(
    help="Manage the local file workspace (privacy-first; nothing leaves your machine).",
    no_args_is_help=True,
)
sessions_app = typer.Typer(help="Manage saved chat sessions.", no_args_is_help=True)
app.add_typer(config_app, name="config")
app.add_typer(models_app, name="models")
app.add_typer(files_app, name="files")
app.add_typer(sessions_app, name="sessions")


@app.callback()
def _root(
    ctx: typer.Context,
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Write operational logs (no message content) to ~/.inclave/log/inclave.log.",
    ),
    no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI colors in all output."),
) -> None:
    """Global flags applied before any subcommand runs."""
    global console, err_console
    setup_logging(debug=debug)
    if no_color:
        # Rebuild module-level consoles with color stripped. Rich also honors
        # the NO_COLOR env var; setting it lets nested Consoles inherit.
        import os

        os.environ["NO_COLOR"] = "1"
        console = Console(no_color=True, highlight=False)
        err_console = Console(stderr=True, no_color=True, highlight=False)
    log.debug("inclave invoked (debug=%s no_color=%s)", debug, no_color)

    # Bare `inclave` with no subcommand → drop into chat. We call chat()
    # with explicit defaults rather than ctx.invoke() because Typer's option
    # descriptors aren't resolved unless click parses argv into them.
    if ctx.invoked_subcommand is None:
        chat(model=None, file_refs=[], resume=False)


def _exit_code_for(error: InClaveError) -> int:
    from inclave_core import ConfigError, SandboxError

    if isinstance(error, OllamaUnavailableError):
        return EXIT_OLLAMA_UNAVAILABLE
    if isinstance(error, ConfigError):
        return EXIT_CONFIG
    if isinstance(error, SandboxError):
        return EXIT_SANDBOX
    return EXIT_USER


def _fail(error: InClaveError) -> None:
    err_console.print(f"[red]error:[/red] {error}")
    raise typer.Exit(code=_exit_code_for(error))


def _human_size(n: int) -> str:
    size: float = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


@app.command()
def init() -> None:
    """Create ~/.inclave/{config.json,sessions/,log/,workspaces/}.

    Not required for normal use — `inclave chat` sets everything up on first
    run. Kept around for scripted provisioning.
    """
    try:
        d = enclave_dir()
        sessions_dir()
        log_dir()
        cfg = load_config()
    except InClaveError as e:
        _fail(e)
        return

    console.print(f"[green]✓[/green] inclave home: {d}")
    if cfg.default_model is None:
        console.print(
            "[dim]tip: just run [bold]inclave[/bold] — i'll handle Ollama and model setup.[/dim]"
        )
    else:
        console.print(f"[green]✓[/green] default model: {cfg.default_model}")


@config_app.command("show")
def config_show() -> None:
    """Print current configuration."""
    try:
        cfg = load_config()
    except InClaveError as e:
        _fail(e)
        return

    table = Table(title="inclave config", show_lines=False)
    table.add_column("key", style="cyan")
    table.add_column("value")
    for key in CONFIG_KEYS:
        val = getattr(cfg, key)
        table.add_row(key, "—" if val is None else str(val))
    console.print(table)


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    """Set a configuration value.

    Keys: default_model, sandbox_cpu_seconds, sandbox_memory_mb, auto_run.
    """
    try:
        set_config_value(key, value)
    except InClaveError as e:
        _fail(e)
        return
    console.print(f"[green]✓[/green] {key} = {value}")


@models_app.command("list")
def models_list() -> None:
    """List locally available Ollama models."""
    from inclave_ollama.api import list_models

    try:
        models = list_models()
    except InClaveError as e:
        _fail(e)
        return

    if not models:
        console.print(
            "[yellow]no models installed.[/yellow] pull one with: [bold]ollama pull llama3.2[/bold]"
        )
        return

    table = Table(title="ollama models")
    table.add_column("name", style="cyan")
    table.add_column("size")
    table.add_column("family")
    table.add_column("params")
    table.add_column("default", justify="center")
    for m in models:
        size_gb = m.size_bytes / (1024**3) if m.size_bytes else 0
        table.add_row(
            m.name,
            f"{size_gb:.1f} GB" if size_gb else "—",
            m.family or "—",
            m.parameter_count or "—",
            "✓" if m.is_default else "",
        )
    console.print(table)


@models_app.command("pull")
def models_pull(name: str) -> None:
    """Pull a model by name (streams progress)."""
    from inclave_ollama.api import pull_model

    try:
        for line in pull_model(name):
            console.print(line)
    except InClaveError as e:
        _fail(e)
        return
    console.print(f"[green]✓[/green] pulled {name}")


@models_app.command("remove")
def models_remove(name: str) -> None:
    """Remove a locally installed model."""
    from inclave_ollama.api import remove_model

    try:
        remove_model(name)
    except InClaveError as e:
        _fail(e)
        return
    console.print(f"[green]✓[/green] removed {name}")


@models_app.command("use")
def models_use(name: str) -> None:
    """Set the default model."""
    from inclave_ollama.api import list_models

    try:
        models = list_models()
    except InClaveError:
        models = []

    if models:
        available = [m.name for m in models]
        match = next(
            (n for n in available if n == name or n.split(":", 1)[0] == name),
            None,
        )
        if match is None:
            err_console.print(
                f"[red]error:[/red] model not installed: {name}\n"
                f"  available: {', '.join(available)}\n"
                f"  pull one with: [bold]ollama pull {name}[/bold]"
            )
            raise typer.Exit(code=EXIT_USER)
        name = match  # resolve to full canonical name e.g. llama3.2 → llama3.2:3b

    try:
        set_config_value("default_model", name)
    except InClaveError as e:
        _fail(e)
        return
    console.print(f"[green]✓[/green] default model: {name}")


@files_app.command("add")
def files_add(paths: list[Path] = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    """Copy one or more files into the local workspace.

    Files are content-hashed; adding the same file twice is a no-op.
    The originals are never modified or deleted.
    """
    try:
        for p in paths:
            entry, was_new = add_file(p)
            tag = "[green]✓ added[/green]" if was_new else "[dim]· already in workspace[/dim]"
            console.print(f"{tag} {entry.id}  {entry.name}  ({_human_size(entry.bytes)})")
    except InClaveError as e:
        _fail(e)


@files_app.command("list")
def files_list() -> None:
    """List files in the workspace."""
    try:
        files = list_files()
    except InClaveError as e:
        _fail(e)
        return

    if not files:
        console.print(
            "[dim]workspace is empty.[/dim] add a file: [bold]inclave files add <path>[/bold]"
        )
        return

    table = Table(title="workspace files")
    table.add_column("id", style="cyan")
    table.add_column("name")
    table.add_column("kind")
    table.add_column("size", justify="right")
    table.add_column("added")
    for f in files:
        table.add_row(f.id, f.name, f.kind, _human_size(f.bytes), f.added_at)
    console.print(table)


@files_app.command("remove")
def files_remove(ref: str = typer.Argument(..., help="File id (8-char) or file name.")) -> None:
    """Remove a file from the workspace (id or name)."""
    try:
        entry = remove_file(ref)
    except InClaveError as e:
        _fail(e)
        return
    console.print(f"[green]✓[/green] removed {entry.id}  {entry.name}")


@files_app.command("clear")
def files_clear(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """Remove every file from the workspace."""
    if not yes:
        if not typer.confirm("clear all files from the workspace?"):
            console.print("[dim]aborted[/dim]")
            return
    try:
        n = clear_workspace()
    except InClaveError as e:
        _fail(e)
        return
    console.print(f"[green]✓[/green] removed {n} file{'s' if n != 1 else ''}")


@files_app.command("show")
def files_show(
    ref: str = typer.Argument(..., help="File id or name."),
    bytes_: int = typer.Option(2048, "--bytes", help="Max bytes of extracted text to show."),
) -> None:
    """Show the parsed/extracted text for a workspace file."""
    from inclave_core import find_file

    from inclave_cli.files import parse

    try:
        entry = find_file(ref)
        text = parse(entry.stored_path())
    except InClaveError as e:
        _fail(e)
        return

    if len(text.encode("utf-8")) > bytes_:
        text = text.encode("utf-8")[:bytes_].decode("utf-8", errors="replace") + "\n…"
    console.print(Panel(text, title=f"{entry.id} · {entry.name}", border_style="cyan"))


@app.command()
def chat(
    model: str | None = typer.Option(None, "--model", "-m", help="Override default model."),
    file_refs: list[str] = typer.Option(
        None, "--file", "-f", help="Attach a workspace file by id or name (repeatable)."
    ),
    resume: bool = typer.Option(
        False, "--resume", help="Reload the most recent chat (~/.inclave/sessions/last.json)."
    ),
) -> None:
    """Start an interactive chat REPL (multi-turn, streaming, slash commands).

    The REPL opens immediately. If Ollama isn't running or no model is set,
    the banner shows that — type `/setup` to fix it from inside, or just send
    a message and the error will surface inline.
    """
    from inclave_cli.chat import run_chat
    from inclave_cli.onboarding import ensure_dirs

    try:
        ensure_dirs()
        cfg = load_config()
        chosen = model or cfg.default_model or ""
        log.debug("chat start model=%s resume=%s", chosen or "(none)", resume)
        code = run_chat(
            console,
            err_console,
            chosen,
            file_refs=file_refs or None,
            config=cfg,
            resume=resume,
        )
    except InClaveError as e:
        log.warning("chat exit on error: %s", type(e).__name__)
        _fail(e)
        return
    if code != 0:
        raise typer.Exit(code=code)


@sessions_app.command("list")
def sessions_list() -> None:
    """List saved chat sessions."""
    items = list_sessions()
    if not items:
        console.print("[dim]no sessions saved yet.[/dim]")
        return
    table = Table(title="chat sessions")
    table.add_column("name", style="cyan")
    table.add_column("saved at")
    for name, ts in items:
        table.add_row(name, ts or "—")
    console.print(table)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to send to the model."),
    model: str | None = typer.Option(None, "--model", "-m", help="Override default model."),
    file_refs: list[str] = typer.Option(
        None, "--file", "-f", help="Attach a workspace file by id or name (repeatable)."
    ),
    no_files: bool = typer.Option(False, "--no-files", help="Don't auto-attach workspace files."),
) -> None:
    """Ask a one-shot question over the workspace files."""
    from inclave_ollama.api import generate

    from inclave_cli.context import (
        SYSTEM_PROMPT,
        assemble_user_prompt,
        attach,
        select_files,
    )
    from inclave_cli.onboarding import ensure_default_model, ensure_dirs, ensure_ollama_running

    try:
        ensure_dirs()
        ensure_ollama_running(console, err_console)
        cfg = load_config()
        chosen = model or cfg.default_model
        if not chosen:
            # Reuse the model picker (interactive when a TTY, raises otherwise).
            chosen = ensure_default_model(console, err_console)

        if no_files:
            entries = []
        else:
            entries = select_files(file_refs or None)

        attached, warnings = attach(entries)
        for w in warnings:
            err_console.print(f"[yellow]warn:[/yellow] {w}")
        if attached:
            shown = ", ".join(a.entry.name for a in attached)
            console.print(f"[dim]attached: {shown}[/dim]")

        prompt = assemble_user_prompt(question, attached)
        log.debug("ask: model=%s files=%d prompt_bytes=%d", chosen, len(attached), len(prompt))
        answer = generate(prompt, model=chosen, system=SYSTEM_PROMPT)
        log.debug("ask: ok bytes=%d", len(answer))
    except InClaveError as e:
        log.warning("ask: failed (%s)", type(e).__name__)
        _fail(e)
        return
    console.print(answer)


@app.command()
def run(path: str = typer.Argument(..., help="Python file to run, or '-' for stdin.")) -> None:
    """Execute a Python script in the sandbox at the current working directory."""
    from inclave_sandbox import SandboxPolicy, execute_python

    try:
        if path == "-":
            code = sys.stdin.read()
            label = "<stdin>"
        else:
            p = Path(path)
            if not p.is_file():
                raise CLIError(f"file not found: {path}")
            code = p.read_text(encoding="utf-8")
            label = str(p)

        cfg = load_config()
        policy = SandboxPolicy(
            workdir=Path.cwd().resolve(),
            cpu_seconds=cfg.sandbox_cpu_seconds,
            memory_mb=cfg.sandbox_memory_mb,
        )
        log.debug(
            "run: src=%s cpu=%ds mem=%dMB",
            label,
            cfg.sandbox_cpu_seconds,
            cfg.sandbox_memory_mb,
        )
        result = execute_python(code, policy)
        log.debug(
            "run: exit=%d timed_out=%s duration_ms=%d",
            result.exit_code,
            result.timed_out,
            result.duration_ms,
        )
    except InClaveError as e:
        log.warning("run: failed (%s)", type(e).__name__)
        _fail(e)
        return

    if result.stdout:
        console.print(
            Panel(result.stdout.rstrip(), title=f"stdout · {label}", border_style="green")
        )
    if result.stderr:
        console.print(Panel(result.stderr.rstrip(), title="stderr", border_style="red"))

    status = "timed out" if result.timed_out else f"exit {result.exit_code}"
    console.print(f"[dim]sandbox · {status} · {result.duration_ms} ms[/dim]")
    if result.exit_code != 0 or result.timed_out:
        raise typer.Exit(code=EXIT_SANDBOX)


if __name__ == "__main__":
    app()
