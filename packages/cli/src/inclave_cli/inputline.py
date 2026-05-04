"""Interactive input line with slash-command completion.

Wraps prompt_toolkit so the chat REPL can offer:
  - Up/Down to scroll history
  - Type `/` to open a command popup; ↑/↓ to pick, Enter/Tab to insert
  - `/file ` and `/detach ` get filesystem / workspace completion
  - Esc to close the popup

The chat layer treats this as a single function `read_input(reader, prompt)`.
A no-op reader (just calls input()) is used in tests so we don't need a TTY.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    PathCompleter,
)
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory


@dataclass(frozen=True)
class SlashCommand:
    name: str  # without leading slash
    summary: str
    needs_arg: str | None = None  # "path" | "workspace" | "model" | None


COMMANDS: list[SlashCommand] = [
    SlashCommand("help", "show available commands"),
    SlashCommand("files", "list files attached to this session"),
    SlashCommand("file", "attach a file (path or @id)", needs_arg="path"),
    SlashCommand("detach", "detach a file from this session", needs_arg="workspace"),
    SlashCommand("run", "run the last python block in the sandbox"),
    SlashCommand("clear", "wipe conversation (keeps files)"),
    SlashCommand("reset", "wipe conversation AND files"),
    SlashCommand("model", "switch model (lists installed models)", needs_arg="model"),
    SlashCommand("exit", "quit (or Ctrl+D)"),
]


class _SlashCompleter(Completer):
    """Completes slash commands and their arguments."""

    def __init__(
        self,
        list_workspace_refs: Callable[[], Iterable[str]],
        list_model_names: Callable[[], Iterable[str]] | None = None,
    ) -> None:
        self._list_workspace_refs = list_workspace_refs
        self._list_model_names = list_model_names or (lambda: [])
        self._path = PathCompleter(expanduser=True, only_directories=False)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text = document.text_before_cursor

        if not text.startswith("/"):
            return

        # Decide whether we're completing the command name or its argument.
        if " " not in text:
            # Completing /<name>
            prefix = text[1:]
            for cmd in COMMANDS:
                if cmd.name.startswith(prefix.lower()):
                    yield Completion(
                        text=f"/{cmd.name}",
                        start_position=-len(text),
                        display=HTML(f"<cmd>/{cmd.name}</cmd>  <hint>{cmd.summary}</hint>"),
                    )
            return

        # We've passed the first space — complete the argument.
        cmd_word, _, arg = text.partition(" ")
        cmd_name = cmd_word[1:].lower()
        matched: SlashCommand | None = next((c for c in COMMANDS if c.name == cmd_name), None)
        if matched is None or matched.needs_arg is None:
            return

        if matched.needs_arg == "path":
            arg_doc = Document(text=arg, cursor_position=len(arg))
            yield from self._path.get_completions(arg_doc, complete_event)
        elif matched.needs_arg == "workspace":
            for ref in self._list_workspace_refs():
                if ref.startswith(arg):
                    yield Completion(
                        text=ref,
                        start_position=-len(arg),
                        display=HTML(f"<cmd>{ref}</cmd>"),
                    )
        elif matched.needs_arg == "model":
            for name in self._list_model_names():
                if name.startswith(arg) or name.split(":", 1)[0].startswith(arg):
                    yield Completion(
                        text=name,
                        start_position=-len(arg),
                        display=HTML(f"<cmd>{name}</cmd>"),
                    )


def make_session(
    list_workspace_refs: Callable[[], Iterable[str]],
    list_model_names: Callable[[], Iterable[str]] | None = None,
) -> PromptSession[str]:
    """Construct a prompt_toolkit session for the chat loop."""
    from prompt_toolkit.styles import Style

    style = Style.from_dict(
        {
            # Match the terminal background; a single dim accent for the
            # selected row. The display HTML below uses the "cmd"/"hint"
            # classes so the selection state can override their colors.
            "completion-menu": "bg:default",
            "completion-menu.completion": "bg:default fg:default",
            "completion-menu.completion.current": "bg:#1f3447 fg:default noreverse",
            "completion-menu.meta.completion": "bg:default fg:#6c7a89",
            "completion-menu.meta.completion.current": "bg:#1f3447 fg:#9aa6b3",
            "completion-menu.multi-column-meta": "bg:default fg:#6c7a89",
            "scrollbar.background": "bg:default",
            "scrollbar.button": "bg:#3a4452",
            "auto-suggestion": "fg:#4a5564 italic",
            # Custom classes used inside Completion display HTML.
            "cmd": "fg:#5fb3d1 bold",
            "cmd.current": "fg:#9ad3e8 bold",
            "hint": "fg:#6c7a89",
            "hint.current": "fg:#aebac5",
        }
    )

    return PromptSession(
        history=InMemoryHistory(),
        completer=_SlashCompleter(list_workspace_refs, list_model_names),
        complete_while_typing=True,
        mouse_support=False,
        style=style,
    )


def read_input(session: PromptSession[str], prompt_html: str) -> str:
    """Read one line from the user. Raises EOFError / KeyboardInterrupt as usual."""
    return session.prompt(HTML(prompt_html))
