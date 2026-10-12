"""MatchIndex: end-inclusive range reads with a max-duration lookback, and the airing-or-next lookup."""

from datetime import UTC, datetime

from custom_components.xmltv_calendar.xmltv.model import Programme
from custom_components.xmltv_calendar.xmltv.window import MatchIndex


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 13, hour, minute, tzinfo=UTC)


def _programme(title: str, start: datetime, stop: datetime) -> Programme:
    return Programme(
        channel_id="ch.example",
        start=start,
        stop=stop,
        titles=(title,),
        sub_titles=(),
        description=None,
        categories=(),
        episode=None,
    )


A = _programme("A", _at(12), _at(14))
B = _programme("B", _at(14), _at(15))
L = _programme("L", _at(0), _at(23))
# Deliberately not in start order: the index sorts
INDEX = MatchIndex([B, A, L])


def _titles(programmes: list[Programme]) -> list[str]:
    return [p.title for p in programmes]


def test_len() -> None:
    assert len(INDEX) == 3
    assert len(MatchIndex([])) == 0


def test_overlapping_includes_programme_ending_at_range_start() -> None:
    assert _titles(INDEX.overlapping(_at(14), _at(15))) == ["L", "A", "B"]


def test_overlapping_excludes_programme_starting_at_range_end() -> None:
    assert "A" not in _titles(INDEX.overlapping(_at(10), _at(12)))


def test_overlapping_spanning_programme() -> None:
    assert "A" in _titles(INDEX.overlapping(_at(12, 30), _at(13)))


def test_overlapping_long_programme_lookback() -> None:
    # L started 22 h before the range; only the max-duration lookback finds it
    assert _titles(INDEX.overlapping(_at(22), _at(22, 30))) == ["L"]


def test_overlapping_sorted_by_start() -> None:
    result = INDEX.overlapping(_at(0), _at(23, 59))
    assert [p.start for p in result] == sorted(p.start for p in result)
    assert _titles(result) == ["L", "A", "B"]


def test_empty_index() -> None:
    empty = MatchIndex([])
    assert empty.overlapping(_at(0), _at(23)) == []
    assert empty.current_or_next(_at(12)) is None


def test_current_or_next_boundaries() -> None:
    only_a_b = MatchIndex([A, B])
    assert only_a_b.current_or_next(_at(12, 30)) is A
    # A's stop is not after 14:00, so B is current
    assert only_a_b.current_or_next(_at(14)) is B
    assert only_a_b.current_or_next(_at(23, 30)) is None
    # Before anything airs: the next one
    assert only_a_b.current_or_next(_at(11)) is A


def test_current_or_next_prefers_earliest_airing_match() -> None:
    # L (00:00-23:00) is airing at 12:30 alongside A and started first
    assert INDEX.current_or_next(_at(12, 30)) is L
    assert INDEX.current_or_next(_at(23, 30)) is None
