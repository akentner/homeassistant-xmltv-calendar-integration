"""
Per-calendar match records: the seen-set of the new-match event (EVT-08) and the retained past matches (EVT-07).

A match is new when its UID (`render.event_uid`) is not in the calendar's seen-set and it has not started yet. Every
match a refilter sees joins the seen-set, mapped to its stop as integer epoch seconds for pruning (D-13).

A match that has ended is retained with its raw programme data and channel name (D-16, D-17), so it stays in the
calendar for the calendar's retention days after the feed drops it; feed matches win on a UID collision (D-18).

The stored shape is `{"calendars": {"<subentry_id>": {"seen": {"<uid>": <stop epoch>}, "retained": [...]}}}`. Reading
it is tolerant: a malformed item is dropped and never raises, so a hand-edited store at worst re-baselines silently
(T-04-11).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .model import Programme
from .render import event_uid

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .model import Channel


@dataclass(slots=True, frozen=True)
class RetainedMatch:
    """An ended match kept after the feed may have dropped it: raw programme data plus the channel's name (D-17)."""

    programme: Programme
    channel_name: str


@dataclass(slots=True, frozen=True)
class CalendarMatches:
    """
    One calendar's match record. Never mutated.

    `seen` maps UID to programme stop as integer epoch seconds; `retained` holds the ended matches kept for the
    calendar's retention days.
    """

    seen: Mapping[str, int] = field(default_factory=dict)
    retained: tuple[RetainedMatch, ...] = ()


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


def capture_ended(
    retained: Sequence[RetainedMatch],
    candidates: Iterable[Programme],
    channels: Mapping[str, Channel],
    now: datetime,
) -> tuple[RetainedMatch, ...]:
    """
    Return `retained` plus the candidates that ended at or before `now` and are not retained yet (D-16).

    The channel name is the channel's display name, else the name a retained match on that channel has, else the
    channel ID, so a retained match keeps its channel name after the channel left the feed (RESEARCH Pitfall 11).
    """
    uids = {event_uid(item.programme) for item in retained}
    names = {item.programme.channel_id: item.channel_name for item in retained}
    added: list[RetainedMatch] = []
    for programme in candidates:
        if programme.stop > now:
            continue
        uid = event_uid(programme)
        if uid in uids:
            continue
        uids.add(uid)
        channel = channels.get(programme.channel_id)
        name = channel.display_name if channel is not None else names.get(programme.channel_id, programme.channel_id)
        added.append(RetainedMatch(programme=programme, channel_name=name))
    return (*retained, *added)


def prune_retained(retained: Sequence[RetainedMatch], cutoff: datetime) -> tuple[RetainedMatch, ...]:
    """Return the retained matches whose programme stopped at or after `cutoff`."""
    return tuple(item for item in retained if item.programme.stop >= cutoff)


def merge_matches(feed: Sequence[Programme], retained: Sequence[RetainedMatch]) -> list[Programme]:
    """Return the feed matches plus the retained programmes whose UID the feed matches lack; the feed wins (D-18)."""
    feed_uids = {event_uid(programme) for programme in feed}
    return [*feed, *(item.programme for item in retained if event_uid(item.programme) not in feed_uids)]


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def _retained_to_dict(item: RetainedMatch) -> dict[str, Any]:
    programme = item.programme
    return {
        "channel_id": programme.channel_id,
        "channel_name": item.channel_name,
        "start": _iso(programme.start),
        "stop": _iso(programme.stop),
        "titles": list(programme.titles),
        "sub_titles": list(programme.sub_titles),
        "description": programme.description,
        "categories": list(programme.categories),
        "episode": programme.episode,
    }


def records_to_dict(records: Mapping[str, CalendarMatches]) -> dict[str, Any]:
    """Return the JSON-ready stored form of all calendars' records."""
    return {
        "calendars": {
            subentry_id: {
                "seen": dict(record.seen),
                "retained": [_retained_to_dict(item) for item in record.retained],
            }
            for subentry_id, record in records.items()
        }
    }


def _seen_from(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        uid: stop
        for uid, stop in value.items()
        if isinstance(uid, str) and isinstance(stop, int) and not isinstance(stop, bool)
    }


def _retained_item(value: dict[str, Any]) -> RetainedMatch:
    return RetainedMatch(
        programme=Programme(
            channel_id=value["channel_id"],
            start=datetime.fromisoformat(value["start"]),
            stop=datetime.fromisoformat(value["stop"]),
            titles=tuple(value["titles"]),
            sub_titles=tuple(value["sub_titles"]),
            description=value["description"],
            categories=tuple(value["categories"]),
            episode=value["episode"],
        ),
        channel_name=value["channel_name"],
    )


def _retained_from(value: object) -> tuple[RetainedMatch, ...]:
    if not isinstance(value, list):
        return ()
    items: list[RetainedMatch] = []
    for item in value:
        try:
            items.append(_retained_item(item))
        except KeyError, TypeError, ValueError:
            continue
    return tuple(items)


def records_from_dict(value: object) -> dict[str, CalendarMatches]:
    """Read the stored form; anything malformed reads as empty or drops the bad item, never raises."""
    calendars = value.get("calendars") if isinstance(value, dict) else None
    if not isinstance(calendars, dict):
        return {}
    return {
        subentry_id: CalendarMatches(
            seen=_seen_from(record.get("seen")), retained=_retained_from(record.get("retained"))
        )
        for subentry_id, record in calendars.items()
        if isinstance(subentry_id, str) and isinstance(record, dict)
    }
