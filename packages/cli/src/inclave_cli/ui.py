"""Visual primitives for the chat REPL.

Goal: a quiet, Claude-Code-like surface — minimal chrome, lots of vertical air,
dim metadata, color reserved for state (green ok, red error, cyan accent).
"""

from __future__ import annotations

from collections.abc import Iterable

from inclave_core import FileEntry
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.syntax import Syntax

PROMPT = "[bold cyan]›[/bold cyan] "
ACCENT = "cyan"
DIM = "dim white"

DOT_OK = "[green]●[/green]"
DOT_BAD = "[red]●[/red]"
DOT_PEND = "[yellow]●[/yellow]"


def banner(console: Console, model: str, n_files: int, workdir: str) -> None:
    pieces = [
        f"{DOT_OK} [bold]inclave[/bold]",
        f"[{DIM}]{model}[/{DIM}]",
        f"[{DIM}]workspace: {n_files} file{'s' if n_files != 1 else ''}[/{DIM}]",
        f"[{DIM}]workdir: {workdir}[/{DIM}]",
    ]
    console.print("  ".join(pieces))
    console.print(
        f"[{DIM}]/help for commands · drop a file path to attach · Ctrl+D to exit[/{DIM}]"
    )
    console.print()


def info(console: Console, msg: str) -> None:
    console.print(f"[{DIM}]{msg}[/{DIM}]")


def ok(console: Console, msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def warn(console: Console, msg: str) -> None:
    console.print(f"[yellow]![/yellow] {msg}")


def error(console: Console, msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")


def section_rule(console: Console, label: str) -> None:
    console.rule(f"[{DIM}]{label}[/{DIM}]", align="left", style=DIM)


def render_files(
    console: Console,
    entries: Iterable[FileEntry],
    *,
    attached_ids: set[str] | None = None,
    title: str | None = None,
) -> None:
    entries = list(entries)
    if not entries:
        info(console, "workspace is empty")
        return
    if title:
        info(console, title)
    attached_ids = attached_ids or set()
    width = max((len(e.name) for e in entries), default=0)
    for e in entries:
        marker = DOT_OK if e.id in attached_ids else f"[{DIM}]·[/{DIM}]"
        name_padded = e.name.ljust(width)
        console.print(
            f"  {marker} [{ACCENT}]{e.id}[/{ACCENT}]  {name_padded}  "
            f"[{DIM}]{e.kind} · {_fmt_size(e.bytes)}[/{DIM}]"
        )


def render_code_proposal(console: Console, code: str) -> None:
    syntax = Syntax(
        code,
        "python",
        line_numbers=True,
        theme="ansi_dark",
        background_color="default",
        word_wrap=True,
    )
    console.print(Panel(syntax, title="proposed code", border_style=DIM, padding=(0, 1)))


def render_sandbox_output(
    console: Console,
    *,
    stdout: str,
    stderr: str,
    exit_code: int,
    duration_ms: int,
    timed_out: bool,
) -> None:
    if stdout.strip():
        console.print(
            Panel(
                stdout.rstrip(),
                title="[green]stdout[/green]",
                border_style="green",
                padding=(0, 1),
            )
        )
    if stderr.strip():
        console.print(
            Panel(
                stderr.rstrip(),
                title="[red]stderr[/red]",
                border_style="red",
                padding=(0, 1),
            )
        )
    if timed_out:
        status = "[red]timed out[/red]"
    elif exit_code == 0:
        status = "[green]exit 0[/green]"
    else:
        status = f"[red]exit {exit_code}[/red]"
    secs = duration_ms / 1000
    duration = f"{duration_ms} ms" if duration_ms < 1000 else f"{secs:.1f}s"
    console.print(f"[{DIM}]ran · {status} · {duration}[/{DIM}]")


def thinking(console: Console) -> Status:
    """Return a Rich Status spinner suitable for `with thinking(console): ...`.

    The caller stops it as soon as the first stream token arrives.
    """
    return console.status(f"[{DIM}]thinking…[/{DIM}]", spinner="dots")


def render_markdown(console: Console, text: str) -> None:
    """Render an assistant turn as Rich Markdown.

    Falls back to plain print if Markdown raises (it's strict about some inputs).
    """
    try:
        console.print(Markdown(text, code_theme="ansi_dark"))
    except Exception:
        console.print(text)


def status_hint(
    console: Console,
    *,
    model: str,
    n_files: int,
    n_turns: int,
    workdir: str,
) -> None:
    """One-line dim summary printed between turns."""
    parts = [
        model,
        f"{n_files} file{'s' if n_files != 1 else ''}",
        f"{n_turns} turn{'s' if n_turns != 1 else ''}",
        f"workdir: {workdir}",
    ]
    console.print(f"[{DIM}]{'  ·  '.join(parts)}[/{DIM}]")


def help_text() -> str:
    return (
        "[bold]commands[/bold]\n"
        "  [cyan]/help[/cyan]                this list\n"
        "  [cyan]/files[/cyan]               files attached to this session\n"
        "  [cyan]/files all[/cyan]           everything in the workspace\n"
        "  [cyan]/file[/cyan] <path>         attach a local file (also: drop a path)\n"
        "  [cyan]/file[/cyan] @<id|name>     attach something already in the workspace\n"
        "  [cyan]/detach[/cyan] <id|name>    detach from this session\n"
        "  [cyan]/run[/cyan]                 run the last python block in the sandbox\n"
        "  [cyan]/clear[/cyan]               wipe conversation (keeps files)\n"
        "  [cyan]/reset[/cyan]               wipe conversation AND files\n"
        "  [cyan]/exit[/cyan]                quit (also: bare `exit`, `quit`, or Ctrl+D)\n"
        "\n"
        "[bold]drag & drop[/bold]\n"
        "  drop a file from Finder onto the prompt — it's attached automatically.\n"
        "  multiple paths in one line work too. globs (*.csv) supported."
    )


def _fmt_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
