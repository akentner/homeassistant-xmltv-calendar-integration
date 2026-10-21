"""
Per-calendar seen-set of the new-match event (EVT-08, D-08, D-09).

A match is new when its UID (`render.event_uid`) is not in the calendar's seen-set and it has not started yet. Every
match a refilter sees joins the seen-set, mapped to its stop as integer epoch seconds for pruning (D-13).

The stored shape is `{"calendars": {"<subentry_id>": {"seen": {"<uid>": <stop epoch>}}}}`. Reading it is tolerant: a
malformed item is dropped and never raises, so a hand-edited store at worst re-baselines silently (T-04-11).
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .render import event_uid

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from .model import Programme


@dataclass(slots=True, frozen=True)
class CalendarMatches:
    """One calendar's match record; `seen` maps UID to programme stop as integer epoch seconds. Never mutated."""

    seen: Mapping[str, int] = field(default_factory=dict)


def _order(programme: Programme) -> tuple[datetime, str, str]:
    return programme.start, programme.channel_id, programme.title


def new_matches(
    matches: Sequence[Programme], seen: Mapping[str, int], now: datetime
) -> tuple[list[Programme], dict[str, int]]:
    """
    Return the unseen matches starting after `now` (earliest first) and the seen-set with every given match added.

    Matches that have started or ended join the seen-set silently (D-09); a start equal to `now` does not count.
    """
    new: list[Programme] = []
    updated = dict(seen)
    for programme in matches:
        uid = event_uid(programme)
        if uid not in updated and programme.start > now:
            new.append(programme)
        updated[uid] = int(programme.stop.timestamp())
    new.sort(key=_order)
    return new, updated


def split_announcements(new: Sequence[Programme], limit: int) -> tuple[list[Programme], int]:
    """Return the first `limit` of the already ordered new matches and how many are left unannounced (D-12)."""
    return list(new[:limit]), max(len(new) - limit, 0)


def prune_seen(seen: Mapping[str, int], cutoff: datetime) -> dict[str, int]:
    """Return the entries whose programme stopped at or after `cutoff`; older ones can never fire again (D-13)."""
    limit = int(cutoff.timestamp())
    return {uid: stop for uid, stop in seen.items() if stop >= limit}


def records_to_dict(records: Mapping[str, CalendarMatches]) -> dict[str, Any]:
    """Return the JSON-ready stored form of all calendars' records."""
    return {"calendars": {subentry_id: {"seen": dict(record.seen)} for subentry_id, record in records.items()}}


def _seen_from(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        uid: stop
        for uid, stop in value.items()
        if isinstance(uid, str) and isinstance(stop, int) and not isinstance(stop, bool)
    }


def records_from_dict(value: object) -> dict[str, CalendarMatches]:
    """Read the stored form; anything malformed reads as empty or drops the bad item, never raises."""
    calendars = value.get("calendars") if isinstance(value, dict) else None
    if not isinstance(calendars, dict):
        return {}
    return {
        subentry_id: CalendarMatches(seen=_seen_from(record.get("seen")))
        for subentry_id, record in calendars.items()
        if isinstance(subentry_id, str) and isinstance(record, dict)
    }
