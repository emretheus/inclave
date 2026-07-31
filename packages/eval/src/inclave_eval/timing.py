"""Latency instrumentation for streamed replies.

Wraps any chunk iterator and records time-to-first-token separately from total
duration. Time-to-first-token is the figure that tracks perceived speed: a run
can stream quickly overall yet still feel slow if the model stalls before the
first chunk, and a single total-duration number cannot distinguish the two.

Uses `perf_counter` (monotonic) so the numbers stay valid across wall-clock
adjustments such as NTP steps or DST.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from time import perf_counter

from .types import Timing


class StreamTimer:
    """Collects timing while a reply streams.

    Usage:
        timer = StreamTimer()
        text = "".join(timer.wrap(chunks))
        timing = timer.result()
    """

    def __init__(self) -> None:
        self._start: float | None = None
        self._first: float | None = None
        self._end: float | None = None
        self._tokens = 0

    def wrap(self, chunks: Iterable[str]) -> Iterator[str]:
        """Yield each chunk through, stamping first-token and end times."""
        self._start = perf_counter()
        try:
            for chunk in chunks:
                if self._first is None:
                    self._first = perf_counter()
                # Chunks are not tokens, but they are the only unit the stream
                # exposes; counted as a consistent relative throughput proxy.
                self._tokens += 1
                yield chunk
        finally:
            # Stamped in `finally` so an aborted or failed stream still reports
            # how long it ran before dying, instead of reporting zero.
            self._end = perf_counter()

    def result(self) -> Timing:
        if self._start is None:
            return Timing(first_token_ms=None, total_ms=0.0, token_count=0)
        end = self._end if self._end is not None else perf_counter()
        first_ms = None if self._first is None else (self._first - self._start) * 1000.0
        return Timing(
            first_token_ms=first_ms,
            total_ms=(end - self._start) * 1000.0,
            token_count=self._tokens,
        )
