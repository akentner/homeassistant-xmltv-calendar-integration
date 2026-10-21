"""Seen-set rules of the new-match event: future only, ordering, burst cap, pruning, tolerant reading (D-08..D-13)."""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.xmltv_calendar.xmltv.model import Programme
from custom_components.xmltv_calendar.xmltv.render import event_uid

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


def _programme(title: str, start: datetime, channel_id: str = "ch.example") -> Programme:
    return Programme(
        channel_id=channel_id,
        start=start,
        stop=start + timedelta(minutes=30),
        titles=(title,),
        sub_titles=(),
        description=None,
        categories=(),
        episode=None,
    )


def _epoch(moment: datetime) -> int:
    return int(moment.timestamp())


def test_new_matches_only_future_unseen() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import new_matches

    a = _programme("A", NOW - timedelta(hours=1))
    b = _programme("B", NOW)
    c = _programme("C", NOW + timedelta(hours=1))
    d = _programme("D", NOW + timedelta(hours=2), channel_id="b.de")
    e = _programme("E", NOW + timedelta(hours=2), channel_id="a.de")

    new, seen = new_matches([a, b, c, d, e], {event_uid(c): _epoch(c.stop)}, NOW)

    # D-09: an airing match (A) and one starting exactly now (B) join silently; equal starts order by channel ID
    assert new == [e, d]
    assert seen == {event_uid(p): _epoch(p.stop) for p in (a, b, c, d, e)}


def test_new_matches_keeps_unrelated_seen_entries() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import new_matches

    later = _programme("Later", NOW + timedelta(hours=3))
    new, seen = new_matches([later], {"gone-uid": 5}, NOW)

    assert new == [later]
    assert seen == {"gone-uid": 5, event_uid(later): _epoch(later.stop)}


def test_split_announcements() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import split_announcements

    many = [_programme(f"P{i:02d}", NOW + timedelta(minutes=10 * i)) for i in range(60)]
    assert split_announcements(many, 50) == (many[:50], 10)

    few = many[:3]
    assert split_announcements(few, 50) == (few, 0)


def test_prune_seen() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import prune_seen

    cutoff = NOW - timedelta(days=1)
    seen = {"old": _epoch(cutoff) - 1, "edge": _epoch(cutoff), "new": _epoch(NOW)}

    # The boundary is kept: an entry whose programme stopped exactly at the cutoff stays
    assert prune_seen(seen, cutoff) == {"edge": _epoch(cutoff), "new": _epoch(NOW)}


@pytest.mark.parametrize(
    ("stored", "expected_seen"),
    [
        (None, None),
        ([], None),
        ({"calendars": 5}, None),
        ({"calendars": {"s": 5}}, None),
        ({"calendars": {"s": {"seen": {"u": "1"}}}}, {}),
        ({"calendars": {"s": {"seen": {"u": True}}}}, {}),
        ({"calendars": {"s": {"seen": {"u": 1.5}}}}, {}),
        ({"calendars": {"s": {"seen": [1, 2]}}}, {}),
        ({"calendars": {"s": {"seen": {"u": 7, "bad": None}}}}, {"u": 7}),
    ],
)
def test_records_from_dict_is_tolerant(stored: object, expected_seen: dict[str, int] | None) -> None:
    from custom_components.xmltv_calendar.xmltv.matches import CalendarMatches, records_from_dict

    expected = {} if expected_seen is None else {"s": CalendarMatches(seen=expected_seen)}
    assert records_from_dict(stored) == expected


def test_records_round_trip() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import (
        CalendarMatches,
        records_from_dict,
        records_to_dict,
    )

    records = {"s1": CalendarMatches(seen={"u1": 1, "u2": 2}), "s2": CalendarMatches()}
    assert records_from_dict(records_to_dict(records)) == records
