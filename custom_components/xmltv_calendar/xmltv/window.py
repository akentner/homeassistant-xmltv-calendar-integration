"""Time-window reads over a calendar's matches. Plan 01-04 replaces the scans with an index."""

from operator import attrgetter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from .model import Programme

_START = attrgetter("start")


def overlapping(matches: Sequence[Programme], start: datetime, end: datetime) -> list[Programme]:
    """Return programmes overlapping [start, end), end-inclusive on the programme's stop, sorted by start."""
    return sorted((p for p in matches if p.start < end and p.stop >= start), key=_START)


def current_or_next(matches: Sequence[Programme], now: datetime) -> Programme | None:
    """Return the earliest-start programme that has not ended at `now`."""
    return min((p for p in matches if p.stop > now), key=_START, default=None)
