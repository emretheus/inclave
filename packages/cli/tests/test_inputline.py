"""Tests for the slash-command completer."""

from __future__ import annotations

from inclave_cli.inputline import COMMANDS, _SlashCompleter
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document


def _completions(completer: _SlashCompleter, text: str) -> list[str]:
    doc = Document(text=text, cursor_position=len(text))
    return [c.text for c in completer.get_completions(doc, CompleteEvent())]


def test_slash_alone_lists_all_commands() -> None:
    c = _SlashCompleter(list_workspace_refs=lambda: [])
    out = _completions(c, "/")
    assert sorted(out) == sorted(f"/{cmd.name}" for cmd in COMMANDS)


def test_prefix_filters_commands() -> None:
    c = _SlashCompleter(list_workspace_refs=lambda: [])
    out = _completions(c, "/fi")
    assert "/file" in out and "/files" in out
    assert "/run" not in out


def test_unknown_prefix_yields_nothing() -> None:
    c = _SlashCompleter(list_workspace_refs=lambda: [])
    assert _completions(c, "/zzz") == []


def test_no_completion_for_plain_text() -> None:
    c = _SlashCompleter(list_workspace_refs=lambda: [])
    assert _completions(c, "hello world") == []


def test_detach_completes_workspace_refs() -> None:
    c = _SlashCompleter(list_workspace_refs=lambda: ["abc12345", "report.pdf"])
    out = _completions(c, "/detach ")
    assert "abc12345" in out and "report.pdf" in out


def test_detach_filters_by_prefix() -> None:
    c = _SlashCompleter(list_workspace_refs=lambda: ["abc12345", "xyz67890"])
    out = _completions(c, "/detach abc")
    assert out == ["abc12345"]


def test_command_without_arg_skips_arg_completion() -> None:
    c = _SlashCompleter(list_workspace_refs=lambda: ["a"])
    # /clear takes no argument; once you've typed `/clear ` we offer nothing
    assert _completions(c, "/clear x") == []


def test_model_completes_installed_models() -> None:
    c = _SlashCompleter(
        list_workspace_refs=lambda: [],
        list_model_names=lambda: ["llama3.2:latest", "qwen2.5-coder:14b"],
    )
    out = _completions(c, "/model ")
    assert "llama3.2:latest" in out and "qwen2.5-coder:14b" in out


def test_model_filters_by_prefix() -> None:
    c = _SlashCompleter(
        list_workspace_refs=lambda: [],
        list_model_names=lambda: ["llama3.2:latest", "qwen2.5-coder:14b"],
    )
    out = _completions(c, "/model llama")
    assert out == ["llama3.2:latest"]
