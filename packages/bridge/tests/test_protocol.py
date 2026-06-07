"""Protocol frame construction + schema export."""

from __future__ import annotations

from inclave_bridge import protocol


def test_make_response() -> None:
    r = protocol.make_response(7, {"x": 1})
    assert r == {"jsonrpc": "2.0", "id": 7, "result": {"x": 1}}


def test_make_error_carries_data_code() -> None:
    r = protocol.make_error(3, protocol.INTERNAL_ERROR, "boom", protocol.ERR_SANDBOX)
    assert r["error"]["code"] == protocol.INTERNAL_ERROR
    assert r["error"]["data"]["code"] == "sandbox_error"


def test_make_notification_has_no_id() -> None:
    n = protocol.make_notification("chat.token", {"delta": "hi"})
    assert "id" not in n
    assert n["method"] == "chat.token"


def test_request_from_obj_defaults() -> None:
    req = protocol.Request.from_obj({"method": "config.get"})
    assert req.method == "config.get"
    assert req.params == {}
    assert req.id is None


def test_schema_lists_all_methods_and_events() -> None:
    s = protocol.schema()
    names = {m["name"] for m in s["methods"]}
    assert "chat.send" in names
    assert "models.pull" in names
    assert "config.get" in names
    event_names = {e["name"] for e in s["events"]}
    assert "chat.token" in event_names
    assert "models.pull_progress" in event_names


def test_streaming_methods_flagged() -> None:
    s = protocol.schema()
    by_name = {m["name"]: m for m in s["methods"]}
    assert by_name["chat.send"]["streams"] is True
    assert by_name["config.get"]["streams"] is False
