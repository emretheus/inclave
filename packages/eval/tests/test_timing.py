from __future__ import annotations

from collections.abc import Iterator

import pytest
from inclave_eval.timing import StreamTimer


def test_records_chunks_and_nonnegative_durations() -> None:
    timer = StreamTimer()
    out = "".join(timer.wrap(iter(["a", "b", "c"])))
    t = timer.result()
    assert out == "abc"
    assert t.token_count == 3
    assert t.total_ms >= 0
    assert t.first_token_ms is not None
    # First token cannot arrive after the stream finished.
    assert t.first_token_ms <= t.total_ms + 1e-6


def test_empty_stream_has_no_first_token() -> None:
    timer = StreamTimer()
    assert "".join(timer.wrap(iter([]))) == ""
    t = timer.result()
    assert t.first_token_ms is None
    assert t.token_count == 0


def test_result_before_any_run_is_zeroed() -> None:
    t = StreamTimer().result()
    assert t.total_ms == 0.0
    assert t.first_token_ms is None


def test_failed_stream_still_reports_elapsed_time() -> None:
    """A stream that dies mid-flight must not report zero duration."""

    def boom() -> Iterator[str]:
        yield "a"
        raise RuntimeError("stream died")

    timer = StreamTimer()
    with pytest.raises(RuntimeError):
        list(timer.wrap(boom()))

    t = timer.result()
    assert t.token_count == 1
    assert t.total_ms >= 0
    assert t.first_token_ms is not None


def test_tokens_per_second_is_none_without_data() -> None:
    t = StreamTimer().result()
    assert t.tokens_per_second is None
