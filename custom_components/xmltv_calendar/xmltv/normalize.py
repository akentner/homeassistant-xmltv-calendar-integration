"""Normalization of parsed programmes: stop inference and ordering."""

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import timedelta

    from .model import ParseStats, Programme


def _sort_key(programme: Programme) -> tuple[object, str, str]:
    return (programme.start, programme.channel_id, programme.title)


def normalize_programmes(
    programmes: Iterable[Programme], *, default_duration: timedelta, stats: ParseStats
) -> tuple[Programme, ...]:
    """
    Return the programmes sorted by (start, channel_id, title) with a valid stop.

    The parser passes a missing or unparsable stop as `stop == start`; any stop not after the start gets
    `start + default_duration` and is counted in `stats.inferred_stops`. Plan 01-02 adds next-start inference and dedup.
    """
    result: list[Programme] = []
    for programme in programmes:
        if programme.stop <= programme.start:
            stats.inferred_stops += 1
            result.append(replace(programme, stop=programme.start + default_duration))
        else:
            result.append(programme)
    result.sort(key=_sort_key)
    return tuple(result)
