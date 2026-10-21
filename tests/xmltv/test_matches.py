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


# Retained past matches (EVT-07, D-15..D-18)

CUTOFF = NOW - timedelta(days=1)


def _ended(title: str, stop: datetime, channel_id: str = "ch.example") -> Programme:
    """Return a 30-minute programme that stops at `stop`."""
    return _programme(title, stop - timedelta(minutes=30), channel_id)


def test_capture_ended() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import RetainedMatch, capture_ended
    from custom_components.xmltv_calendar.xmltv.model import Channel

    channels = {"ch.example": Channel("ch.example", "Example TV")}
    old = RetainedMatch(_ended("Old", NOW - timedelta(hours=5)), "Example TV")
    ended = _ended("Ended", NOW - timedelta(hours=1))
    edge = _ended("Edge", NOW)  # stop == now counts as ended (D-16)
    airing = _ended("Airing", NOW + timedelta(minutes=10))
    future = _programme("Future", NOW + timedelta(hours=1))

    result = capture_ended((old,), [ended, edge, airing, future, old.programme, ended], channels, NOW)

    assert result == (old, RetainedMatch(ended, "Example TV"), RetainedMatch(edge, "Example TV"))


def test_capture_ended_channel_name_fallbacks() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import RetainedMatch, capture_ended

    previous = RetainedMatch(_ended("Previous", NOW - timedelta(hours=6), "gone.de"), "Gone TV")
    gone = _ended("Gone", NOW - timedelta(hours=1), "gone.de")
    unknown = _ended("Unknown", NOW - timedelta(hours=1), "unknown.de")

    result = capture_ended((previous,), [gone, unknown], {}, NOW)

    # No channel map entry: the name a retained match on the channel has, else the channel ID (Pitfall 11)
    assert [item.channel_name for item in result] == ["Gone TV", "Gone TV", "unknown.de"]


def test_prune_retained_boundary() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import RetainedMatch, prune_retained

    edge = RetainedMatch(_ended("Edge", CUTOFF), "X")
    early = RetainedMatch(_ended("Early", CUTOFF - timedelta(seconds=1)), "X")

    assert prune_retained((early, edge), CUTOFF) == (edge,)


def test_merge_matches_prefers_feed() -> None:
    from dataclasses import replace

    from custom_components.xmltv_calendar.xmltv.matches import RetainedMatch, merge_matches

    a = _ended("A", NOW - timedelta(hours=2))
    b = _programme("B", NOW + timedelta(hours=1))
    c = _ended("C", NOW - timedelta(hours=3))
    # Same UID as the feed's A, older text: the feed wins (D-18)
    stale_a = replace(a, description="old text")
    retained = (RetainedMatch(stale_a, "X"), RetainedMatch(c, "X"))

    assert merge_matches([a, b], retained) == [a, b, c]
    assert merge_matches([], retained) == [stale_a, c]


def test_retained_cap() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import MAX_RETAINED, RetainedMatch, prune_retained

    items = [RetainedMatch(_ended(f"P{i}", NOW - timedelta(minutes=i)), "X") for i in range(MAX_RETAINED + 3)]
    shuffled = items[1::2] + items[::2]  # not in start order

    result = prune_retained(shuffled, NOW - timedelta(days=7))

    # The latest-starting ones are kept, in start order (T-04-17)
    assert MAX_RETAINED == 5000
    assert result == tuple(sorted(items[:MAX_RETAINED], key=lambda item: item.programme.start))


def _stored_retained() -> dict[str, object]:
    return {
        "channel_id": "daserste.de",
        "channel_name": "Das Erste",
        "start": "2026-10-13T10:00:00+00:00",
        "stop": "2026-10-13T11:30:00+00:00",
        "titles": ["Formel 1", "Formula 1"],
        "sub_titles": ["Qualifying"],
        "description": "Live",
        "categories": ["Sport"],
        "episode": "1.2.",
    }


def test_retained_roundtrip() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import (
        CalendarMatches,
        RetainedMatch,
        records_from_dict,
        records_to_dict,
    )

    full = Programme(
        channel_id="daserste.de",
        start=datetime.fromisoformat("2026-10-13T12:00:00+02:00"),
        stop=datetime.fromisoformat("2026-10-13T13:30:00+02:00"),
        titles=("Formel 1", "Formula 1"),
        sub_titles=("Qualifying",),
        description="Live",
        categories=("Sport", "Motorsport"),
        episode="1.2.",
    )
    bare = _ended("Bare", NOW - timedelta(hours=1))
    records = {
        "s1": CalendarMatches(
            seen={"u": 1}, retained=(RetainedMatch(full, "Das Erste"), RetainedMatch(bare, "ch.example"))
        ),
        "s2": CalendarMatches(),
    }

    assert records_from_dict(records_to_dict(records)) == records


@pytest.mark.parametrize(
    "change",
    [
        pytest.param({"start": "2026-10-13T10:00:00"}, id="naive_start"),
        pytest.param({"stop": "2026-10-13T11:30:00"}, id="naive_stop"),
        pytest.param({"start": "yesterday"}, id="unparsable_start"),
        pytest.param({"start": 1793000000}, id="int_start"),
        pytest.param({"stop": "2026-10-13T09:00:00+00:00"}, id="stop_before_start"),
        pytest.param({"titles": []}, id="empty_titles"),
        pytest.param({"titles": None}, id="none_titles"),
        pytest.param({"titles": ["ok", 5]}, id="non_string_title"),
        pytest.param({"titles": "Formel 1"}, id="string_titles"),
        pytest.param({"channel_id": 5}, id="int_channel_id"),
        pytest.param({"channel_id": ""}, id="empty_channel_id"),
        pytest.param({"channel_name": None}, id="none_channel_name"),
        pytest.param({"sub_titles": None}, id="none_sub_titles"),
        pytest.param({"categories": "Sport"}, id="string_categories"),
        pytest.param({"description": 5}, id="int_description"),
        pytest.param({"episode": ["1"]}, id="list_episode"),
        pytest.param({"stop": None}, id="none_stop"),
    ],
)
def test_retained_roundtrip_and_tolerance(change: dict[str, object]) -> None:
    from custom_components.xmltv_calendar.xmltv.matches import records_from_dict

    good = _stored_retained()
    bad = {**good, **change}
    records = records_from_dict({"calendars": {"s": {"seen": {}, "retained": [good, bad, "junk", 5]}}})

    # Only the valid item survives; nothing raises (T-04-18)
    assert [item.programme.title for item in records["s"].retained] == ["Formel 1"]


def test_retained_missing_or_malformed_list() -> None:
    from custom_components.xmltv_calendar.xmltv.matches import CalendarMatches, records_from_dict

    assert records_from_dict({"calendars": {"s": {"seen": {}}}}) == {"s": CalendarMatches()}
    assert records_from_dict({"calendars": {"s": {"seen": {}, "retained": {"a": 1}}}}) == {"s": CalendarMatches()}
