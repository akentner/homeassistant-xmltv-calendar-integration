"""Normalization of parsed programmes: stop inference and ordering."""

from dataclasses import replace
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
    Return the programmes sorted by (start, channel_id, title) with a valid stop.

    The parser passes a missing or unparsable stop as `stop == start`. Any stop not after the start is inferred from
    the next strictly later start on the same channel, else `start + default_duration`, and counted in
    `stats.inferred_stops`.
    """
    by_channel: dict[str, list[Programme]] = {}
    for programme in programmes:
        by_channel.setdefault(programme.channel_id, []).append(programme)
    result: list[Programme] = []
    for group in by_channel.values():
        group.sort(key=lambda programme: programme.start)  # stable: ties keep input order
        result.extend(_infer_stops(group, default_duration, stats))
    result.sort(key=_sort_key)
    return tuple(result)
