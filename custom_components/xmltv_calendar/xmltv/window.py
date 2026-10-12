"""Time-window reads over a calendar's matches."""

from bisect import bisect_left
from datetime import timedelta
from operator import attrgetter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from .model import Programme

_START = attrgetter("start")


class MatchIndex:
    """Matches sorted by start, with a parallel list of starts and the longest duration for bisect lookups."""

    __slots__ = ("_max_duration", "_programmes", "_starts")

    def __init__(self, matches: Sequence[Programme]) -> None:
        """Index `matches`; the sort is stable and near-linear for the already start-ordered filter output."""
        self._programmes: tuple[Programme, ...] = tuple(sorted(matches, key=_START))
        self._starts: list[datetime] = [p.start for p in self._programmes]
        self._max_duration: timedelta = max((p.stop - p.start for p in self._programmes), default=timedelta(0))

    def __len__(self) -> int:
        """Return the number of indexed matches."""
        return len(self._programmes)

    def overlapping(self, start: datetime, end: datetime) -> list[Programme]:
        """Return matches with start < `end` and stop >= `start` (end-inclusive), sorted by start."""
        # Every candidate starts at or after start - max_duration, so only that slice is scanned
        lo = bisect_left(self._starts, start - self._max_duration)
        hi = bisect_left(self._starts, end)
        return [p for p in self._programmes[lo:hi] if p.stop >= start]

    def current_or_next(self, now: datetime) -> Programme | None:
        """Return the earliest-start match whose stop is after `now` (airing, else the next one)."""
        for i in range(bisect_left(self._starts, now - self._max_duration), len(self._programmes)):
            if (programme := self._programmes[i]).stop > now:
                return programme
        return None


def overlapping(matches: Sequence[Programme], start: datetime, end: datetime) -> list[Programme]:
    """Return programmes overlapping [start, end), end-inclusive on the programme's stop, sorted by start."""
    return sorted((p for p in matches if p.start < end and p.stop >= start), key=_START)


def current_or_next(matches: Sequence[Programme], now: datetime) -> Programme | None:
    """Return the earliest-start programme that has not ended at `now`."""
    return min((p for p in matches if p.stop > now), key=_START, default=None)
