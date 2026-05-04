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
    list_files,
    load_config,
    log_dir,
    remove_file,
    sessions_dir,
    set_config_value,
)
from inclave_core.config import CONFIG_KEYS
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

EXIT_OK = 0
EXIT_USER = 1
EXIT_CONFIG = 2
EXIT_OLLAMA_UNAVAILABLE = 3
EXIT_SANDBOX = 4
EXIT_INTERNAL = 99

app = typer.Typer(
    name="inclave",
    help="Local-first, privacy-preserving CLI for macOS — sandbox + Ollama + file work.",
    no_args_is_help=True,
    add_completion=False,
)

config_app = typer.Typer(help="Manage InClave configuration.", no_args_is_help=True)
models_app = typer.Typer(help="Manage local Ollama models.", no_args_is_help=True)
files_app = typer.Typer(
    help="Manage the local file workspace (privacy-first; nothing leaves your machine).",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")
app.add_typer(models_app, name="models")
app.add_typer(files_app, name="files")


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
    """Create ~/.inclave/{config.json,sessions/,log/,workspaces/}."""
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
            "[yellow]no default model set[/yellow] — run: "
            "[bold]inclave models pull <name>[/bold] then [bold]inclave models use <name>[/bold]"
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
) -> None:
    """Start an interactive chat REPL (multi-turn, streaming, slash commands)."""
    from inclave_cli.chat import run_chat

    try:
        cfg = load_config()
        chosen = model or cfg.default_model
        if not chosen:
            raise CLIError(
                "no model selected. set one with: inclave models use <name>, or pass --model"
            )
        code = run_chat(console, err_console, chosen, file_refs=file_refs or None, config=cfg)
    except InClaveError as e:
        _fail(e)
        return
    if code != 0:
        raise typer.Exit(code=code)


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

    try:
        cfg = load_config()
        chosen = model or cfg.default_model
        if not chosen:
            raise CLIError(
                "no model selected. set one with: inclave models use <name>, or pass --model"
            )

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
        answer = generate(prompt, model=chosen, system=SYSTEM_PROMPT)
    except InClaveError as e:
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
        result = execute_python(code, policy)
    except InClaveError as e:
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
