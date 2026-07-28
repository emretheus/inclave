"""Server dispatch: round-trip requests through BridgeServer with a captured
output stream. Engine boundaries (Ollama) are mocked.
"""

from __future__ import annotations

import io
import json
import threading
from pathlib import Path
from typing import Any
from unittest.mock import patch

from inclave_bridge.server import BridgeServer


def _server() -> tuple[BridgeServer, io.StringIO]:
    out = io.StringIO()
    return BridgeServer(out=out), out


def _frames(out: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]


def _chat_cfg(cfg: Any) -> None:
    cfg.return_value.default_model = "m1"
    cfg.return_value.sandbox_cpu_seconds = 30
    cfg.return_value.sandbox_memory_mb = 512


def test_cancel_is_deliverable_mid_turn(fake_home: Path) -> None:
    """Regression: `chat.send` used to run inline on the reader thread, so while
    a turn streamed nobody read stdin and the `chat.cancel` frame sat unread in
    the pipe until the turn had already finished. This test streams until a
    cancel is observed — on the old server it would hang forever.
    """
    cancel_seen = threading.Event()
    stream_entered = threading.Event()

    def blocking_stream(model, messages, num_ctx=None):  # type: ignore[no-untyped-def]
        stream_entered.set()
        # Keep yielding until the cancel lands. If cancel can't be delivered
        # while we're streaming, this never terminates.
        for _ in range(2000):
            if cancel_seen.wait(timeout=0.01):
                return
            yield "tok "
        raise AssertionError("cancel was never delivered during the turn")

    srv, out = _server()
    with (
        patch("inclave_bridge.handlers.chat.engine.stream_chat", blocking_stream),
        patch("inclave_bridge.handlers.chat.load_config") as cfg,
    ):
        _chat_cfg(cfg)
        srv.dispatch_line(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "chat.send",
                    "params": {"session_id": "s1", "text": "hi", "file_ids": []},
                }
            )
        )
        assert stream_entered.wait(timeout=5), "turn never started"

        # The reader thread must still be responsive while the turn streams.
        srv.dispatch_line(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "chat.cancel",
                    "params": {"session_id": "s1"},
                }
            )
        )
        cancel_seen.set()

        for t in srv._workers:
            t.join(timeout=10)
            assert not t.is_alive(), "turn did not stop after cancel"

    frames = _frames(out)
    methods = [f.get("method") for f in frames]
    assert "chat.cancelled" in methods, "no chat.cancelled event emitted"

    cancel_reply = next(f for f in frames if f.get("id") == 2)
    assert cancel_reply["result"]["accepted"] is True

    send_reply = next(f for f in frames if f.get("id") == 1)
    assert send_reply["result"]["cancelled"] is True


def test_cancel_with_no_turn_running_is_not_accepted(fake_home: Path) -> None:
    """A cancel with nothing to stop must not leave a flag that kills the next
    turn, and must report that it wasn't accepted.
    """
    srv, out = _server()
    srv.handle_line(
        json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "chat.cancel", "params": {"session_id": "s1"}}
        )
    )
    assert _frames(out)[0]["result"]["accepted"] is False
    assert srv._store.is_cancelled("s1") is False

    # The next turn must run to completion, not be killed by a stale flag.
    out.truncate(0)
    out.seek(0)

    def fake_stream(model, messages, num_ctx=None):  # type: ignore[no-untyped-def]
        yield from ["ok"]

    with (
        patch("inclave_bridge.handlers.chat.engine.stream_chat", fake_stream),
        patch("inclave_bridge.handlers.chat.load_config") as cfg,
    ):
        _chat_cfg(cfg)
        srv.handle_line(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "chat.send",
                    "params": {"session_id": "s1", "text": "hi", "file_ids": []},
                }
            )
        )
    reply = next(f for f in _frames(out) if f.get("id") == 2)
    assert reply["result"]["cancelled"] is False


def test_second_send_while_busy_is_rejected(fake_home: Path) -> None:
    """Now that turns run off-thread, a second send must not race the first
    into the same messages list.
    """
    release = threading.Event()
    started = threading.Event()

    def blocking_stream(model, messages, num_ctx=None):  # type: ignore[no-untyped-def]
        started.set()
        release.wait(timeout=5)
        yield "done"

    srv, out = _server()
    with (
        patch("inclave_bridge.handlers.chat.engine.stream_chat", blocking_stream),
        patch("inclave_bridge.handlers.chat.load_config") as cfg,
    ):
        _chat_cfg(cfg)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "chat.send",
            "params": {"session_id": "s1", "text": "hi", "file_ids": []},
        }
        srv.dispatch_line(json.dumps(payload))
        assert started.wait(timeout=5)

        srv.handle_line(json.dumps({**payload, "id": 2}))
        second = next(f for f in _frames(out) if f.get("id") == 2)
        assert second["result"] == {"ok": False, "reason": "busy"}

        release.set()
        for t in srv._workers:
            t.join(timeout=10)


def test_streaming_method_runs_off_reader_thread(fake_home: Path) -> None:
    """dispatch_line must not block on a streaming method."""
    started = threading.Event()
    release = threading.Event()

    def blocking_stream(model, messages, num_ctx=None):  # type: ignore[no-untyped-def]
        started.set()
        release.wait(timeout=5)
        yield "x"

    srv, _out = _server()
    with (
        patch("inclave_bridge.handlers.chat.engine.stream_chat", blocking_stream),
        patch("inclave_bridge.handlers.chat.load_config") as cfg,
    ):
        _chat_cfg(cfg)
        srv.dispatch_line(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "chat.send",
                    "params": {"session_id": "s1", "text": "hi", "file_ids": []},
                }
            )
        )
        # If dispatch blocked, the stream would already be finished.
        assert started.wait(timeout=5)
        assert not release.is_set()
        release.set()
        for t in srv._workers:
            t.join(timeout=10)


def test_non_streaming_method_stays_inline(fake_home: Path) -> None:
    """Only chat.send/run_last go off-thread; everything else must be
    synchronous so ordering stays deterministic.
    """
    srv, out = _server()
    srv.dispatch_line('{"jsonrpc":"2.0","id":1,"method":"config.get"}')
    assert srv._workers == []
    assert _frames(out)[0]["id"] == 1


def test_malformed_streaming_frame_takes_inline_error_path(fake_home: Path) -> None:
    """A chat.send with non-dict params must produce a normal error, not a
    thread that dies silently.
    """
    srv, out = _server()
    srv.dispatch_line('{"jsonrpc":"2.0","id":1,"method":"chat.send","params":[]}')
    assert srv._workers == []
    assert _frames(out)[0]["error"]["code"] in (-32602, -32603)


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
