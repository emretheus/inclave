"""Server dispatch: round-trip requests through BridgeServer with a captured
output stream. Engine boundaries (Ollama) are mocked.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from inclave_bridge.server import BridgeServer


def _server() -> tuple[BridgeServer, io.StringIO]:
    out = io.StringIO()
    return BridgeServer(out=out), out


def _frames(out: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]


def test_config_get_roundtrip(fake_home: Path) -> None:
    srv, out = _server()
    srv.handle_line('{"jsonrpc":"2.0","id":1,"method":"config.get"}')
    frames = _frames(out)
    assert len(frames) == 1
    assert frames[0]["id"] == 1
    assert "default_model" in frames[0]["result"]


def test_unknown_method_errors(fake_home: Path) -> None:
    srv, out = _server()
    srv.handle_line('{"jsonrpc":"2.0","id":9,"method":"nope.nope"}')
    f = _frames(out)[0]
    assert f["error"]["code"] == -32601


def test_parse_error(fake_home: Path) -> None:
    srv, out = _server()
    srv.handle_line("{ not json")
    f = _frames(out)[0]
    assert f["error"]["code"] == -32700


def test_config_set_then_get(fake_home: Path) -> None:
    srv, out = _server()
    srv.handle_line(
        '{"jsonrpc":"2.0","id":1,"method":"config.set",'
        '"params":{"key":"sandbox_cpu_seconds","value":"42"}}'
    )
    f = _frames(out)[0]
    assert f["result"]["sandbox_cpu_seconds"] == 42


def test_invalid_params_missing_key(fake_home: Path) -> None:
    srv, out = _server()
    srv.handle_line('{"jsonrpc":"2.0","id":2,"method":"config.set","params":{"key":"x"}}')
    f = _frames(out)[0]
    # missing "value" -> KeyError -> INVALID_PARAMS
    assert f["error"]["code"] == -32602


def test_files_add_list_remove(fake_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "doc.txt"
    src.write_text("hello")
    srv, out = _server()
    srv.handle_line(
        json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "files.add", "params": {"paths": [str(src)]}}
        )
    )
    added = _frames(out)[0]["result"]
    assert added[0]["name"] == "doc.txt"
    file_id = added[0]["id"]

    out.truncate(0)
    out.seek(0)
    srv.handle_line('{"jsonrpc":"2.0","id":2,"method":"files.list"}')
    listed = _frames(out)[0]["result"]
    assert any(f["id"] == file_id for f in listed)


def test_chat_send_streams_events(fake_home: Path) -> None:
    """chat.send emits token/message_done/turn_done notifications then a result."""

    def fake_stream(model, messages):  # type: ignore[no-untyped-def]
        yield from ["he", "llo"]

    srv, out = _server()
    with (
        patch("inclave_bridge.handlers.chat.engine.stream_chat", fake_stream),
        patch("inclave_bridge.handlers.chat.load_config") as cfg,
    ):
        cfg.return_value.default_model = "m1"
        cfg.return_value.sandbox_cpu_seconds = 30
        cfg.return_value.sandbox_memory_mb = 512
        srv.handle_line(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "chat.send",
                    "params": {"session_id": "s1", "text": "hi", "file_ids": []},
                }
            )
        )

    frames = _frames(out)
    methods = [f.get("method") for f in frames if "method" in f]
    assert "chat.token" in methods
    assert "chat.message_done" in methods
    assert "chat.turn_done" in methods
    # final result frame
    result = [f for f in frames if f.get("id") == 1]
    assert result and result[0]["result"]["ok"] is True


def test_chat_send_no_model_emits_error(fake_home: Path) -> None:
    srv, out = _server()
    with patch("inclave_bridge.handlers.chat.load_config") as cfg:
        cfg.return_value.default_model = ""
        srv.handle_line(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "chat.send",
                    "params": {"session_id": "s1", "text": "hi", "file_ids": []},
                }
            )
        )
    frames = _frames(out)
    errors = [f for f in frames if f.get("method") == "chat.error"]
    assert errors and errors[0]["params"]["code"] == "no_model"


def test_serve_reads_lines(fake_home: Path) -> None:
    srv, out = _server()
    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":1,"method":"config.get"}\n'
        '{"jsonrpc":"2.0","id":2,"method":"system.status"}\n'
    )
    with patch("inclave_bridge.handlers.system._ollama_up", return_value=False):
        rc = srv.serve(stdin=stdin)
    assert rc == 0
    ids = sorted(f["id"] for f in _frames(out))
    assert ids == [1, 2]
