from __future__ import annotations

import json
from pathlib import Path

import pytest
from inclave_eval.cli import main


def test_fixture_run_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "pass rate" in out
    assert "fixture" in out


def test_json_output_written(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dest = tmp_path / "nested" / "eval.json"
    assert main(["--json", str(dest)]) == 0
    payload = json.loads(dest.read_text())
    assert payload["summary"]["pass_rate"] == 1.0
    assert payload["results"]


def test_fail_under_gate_trips(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """--fail-under is what lets CI block an accuracy regression."""
    import inclave_eval.cli as cli
    from inclave_eval.tasks import REGRESSED_REPLIES

    monkeypatch.setattr(cli, "GOOD_REPLIES", REGRESSED_REPLIES)
    assert main(["--fail-under", "50"]) == 1
    assert "below" in capsys.readouterr().err


def test_fail_under_passes_when_above_threshold() -> None:
    assert main(["--fail-under", "100"]) == 0


def test_live_without_model_errors_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Better a clear message than an obscure failure deep in the client."""
    from inclave_core import config as core_config

    monkeypatch.setattr(
        core_config, "load_config", lambda: type("C", (), {"default_model": None})()
    )
    with pytest.raises(SystemExit) as e:
        main(["--live"])
    assert "no model configured" in str(e.value)
