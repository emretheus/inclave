"""Enclave Code CLI entrypoint.

Defines the `enclave` command and its subcommands per PROJECT_PLAN.md §6.
Handlers are stubs for M0; milestone M1+ will implement them.
"""
from __future__ import annotations

import typer

app = typer.Typer(
    name="enclave",
    help="Local-first, privacy-preserving CLI for macOS — sandbox + Ollama + file work.",
    no_args_is_help=True,
    add_completion=False,
)

config_app = typer.Typer(help="Manage Enclave configuration.", no_args_is_help=True)
models_app = typer.Typer(help="Manage local Ollama models.", no_args_is_help=True)
app.add_typer(config_app, name="config")
app.add_typer(models_app, name="models")


@app.command()
def init() -> None:
    """Create ~/.enclave/{config.toml,sessions/,log/}."""
    typer.echo("init: not implemented (M1)")


@config_app.command("show")
def config_show() -> None:
    """Print current configuration."""
    typer.echo("config show: not implemented (M1)")


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    typer.echo(f"config set {key}={value}: not implemented (M1)")


@models_app.command("list")
def models_list() -> None:
    """List locally available Ollama models."""
    typer.echo("models list: not implemented (M1)")


@models_app.command("pull")
def models_pull(name: str) -> None:
    """Pull a model by name."""
    typer.echo(f"models pull {name}: not implemented (M3)")


@models_app.command("remove")
def models_remove(name: str) -> None:
    """Remove a locally installed model."""
    typer.echo(f"models remove {name}: not implemented (M3)")


@models_app.command("use")
def models_use(name: str) -> None:
    """Set the default model."""
    typer.echo(f"models use {name}: not implemented (M1)")


@app.command()
def chat() -> None:
    """Start an interactive chat REPL with optional file context."""
    typer.echo("chat: not implemented (M2)")


@app.command()
def ask(question: str) -> None:
    """Ask a one-shot question, with optional file context."""
    typer.echo(f"ask: not implemented (M1) — received: {question!r}")


@app.command()
def run(path: str) -> None:
    """Execute a Python script in the sandbox at the current working directory."""
    typer.echo(f"run {path}: not implemented (M2)")


if __name__ == "__main__":
    app()