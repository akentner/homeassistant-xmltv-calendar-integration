"""Normalization of parsed programmes: exact-duplicate removal, stop inference and ordering."""

from dataclasses import replace
from datetime import UTC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime, timedelta

    from .model import ParseStats, Programme


def _sort_key(programme: Programme) -> tuple[datetime, str, str]:
    return (programme.start, programme.channel_id, programme.title)


def _infer_stops(group: list[Programme], default_duration: timedelta, stats: ParseStats) -> list[Programme]:
    """
    Give every programme of one channel (sorted by start) a stop later than its start (D-12).

    A stop that is missing (passed as `stop == start`) or not after the start becomes the next strictly later start
    on the channel, else `start + default_duration`.
    """
    result: list[Programme] = []
    block_start: datetime | None = None
    following: datetime | None = None  # start of the next strictly later block
    for programme in reversed(group):
        if programme.start != block_start:
            following, block_start = block_start, programme.start
        if programme.stop <= programme.start:
            stats.inferred_stops += 1
            programme = replace(programme, stop=following or programme.start + default_duration)  # noqa: PLW2901
        result.append(programme)
    result.reverse()  # back to start order, so later stable sorts keep input order for ties
    return result


def normalize_programmes(
    programmes: Iterable[Programme], *, default_duration: timedelta, stats: ParseStats
) -> tuple[Programme, ...]:
    """
    Return the programmes sorted by (start, channel_id, title), without exact duplicates and with a valid stop.

    Exact duplicates (same channel_id, start instant and title) collapse to the first in input order and are counted
    in `stats.duplicates` (EVT-01). The parser passes a missing or unparsable stop as `stop == start`. Any stop not
    after the start is inferred from the next strictly later start on the same channel, else
    `start + default_duration`, and counted in `stats.inferred_stops` (D-12).
    """
    seen: set[tuple[str, datetime, str]] = set()
    by_channel: dict[str, list[Programme]] = {}
    for programme in programmes:
        key = (programme.channel_id, programme.start.astimezone(UTC), programme.title)
        if key in seen:
            stats.duplicates += 1
            continue
        seen.add(key)
        by_channel.setdefault(programme.channel_id, []).append(programme)
    result: list[Programme] = []
    for group in by_channel.values():
        group.sort(key=lambda programme: (programme.start, programme.title))  # stable: ties keep input order
        result.extend(_infer_stops(group, default_duration, stats))
    result.sort(key=_sort_key)
    return tuple(result)
