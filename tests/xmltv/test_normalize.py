"""Normalization: stop inference (D-12), exact-duplicate removal (EVT-01) and deterministic order."""

import random
from datetime import UTC, datetime, timedelta, timezone

from custom_components.xmltv_calendar.xmltv.model import ParseStats, Programme
from custom_components.xmltv_calendar.xmltv.normalize import normalize_programmes

HOUR = timedelta(hours=1)
CEST = timezone(timedelta(hours=2))


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 13, hour, minute, tzinfo=UTC)


def _prog(
    channel: str, start: datetime, title: str, stop: datetime | None = None, description: str | None = None
) -> Programme:
    # A missing stop reaches normalize as stop == start (parser contract from 01-01)
    return Programme(
        channel_id=channel,
        start=start,
        stop=stop or start,
        titles=(title,),
        sub_titles=(),
        description=description,
        categories=(),
        episode=None,
    )


def _normalize(programmes: list[Programme]) -> tuple[tuple[Programme, ...], ParseStats]:
    stats = ParseStats()
    return normalize_programmes(programmes, default_duration=HOUR, stats=stats), stats


def _spans(result: tuple[Programme, ...]) -> list[tuple[str, str, datetime, datetime]]:
    return [(p.channel_id, p.title, p.start, p.stop) for p in result]


def test_missing_stops_inferred_from_next_start() -> None:
    result, stats = _normalize([_prog("x", _at(10), "A"), _prog("x", _at(11), "B"), _prog("x", _at(13), "C")])
    assert _spans(result) == [
        ("x", "A", _at(10), _at(11)),
        ("x", "B", _at(11), _at(13)),
        ("x", "C", _at(13), _at(14)),  # last programme: default 60 minutes
    ]
    assert stats.inferred_stops == 3


def test_stop_not_after_start_is_inferred() -> None:
    result, stats = _normalize(
        [
            _prog("x", _at(10), "Equal", stop=_at(10)),
            _prog("x", _at(11), "Earlier", stop=_at(10, 30)),
            _prog("x", _at(12), "Next"),
        ]
    )
    assert _spans(result)[:2] == [("x", "Equal", _at(10), _at(11)), ("x", "Earlier", _at(11), _at(12))]
    assert stats.inferred_stops == 3


def test_equal_start_different_titles_both_kept() -> None:
    result, stats = _normalize([_prog("x", _at(10), "B"), _prog("x", _at(10), "A"), _prog("x", _at(12), "C")])
    assert _spans(result) == [
        ("x", "A", _at(10), _at(12)),
        ("x", "B", _at(10), _at(12)),
        ("x", "C", _at(12), _at(13)),
    ]
    assert stats.duplicates == 0


def test_exact_duplicates_collapse_first_wins() -> None:
    first = _prog("x", _at(10), "Rennen", stop=_at(12), description="first")
    # Same channel, same instant (different offset), same title: an exact duplicate
    second = _prog("x", datetime(2026, 10, 13, 12, tzinfo=CEST), "Rennen", stop=_at(12), description="second")
    result, stats = _normalize([first, second])
    assert result == (first,)
    assert stats.duplicates == 1


def test_same_title_and_start_on_two_channels_kept() -> None:
    result, stats = _normalize([_prog("y", _at(10), "heute", _at(11)), _prog("x", _at(10), "heute", _at(11))])
    assert [p.channel_id for p in result] == ["x", "y"]
    assert stats.duplicates == 0


def test_back_to_back_not_merged() -> None:
    a = _prog("x", _at(10), "A", stop=_at(11))
    b = _prog("x", _at(11), "B", stop=_at(12))
    result, stats = _normalize([a, b])
    assert result == (a, b)
    assert stats.inferred_stops == 0


def test_shuffled_input_gives_identical_output() -> None:
    programmes = [
        _prog("y", _at(9), "Morgen"),
        _prog("x", _at(10), "B"),
        _prog("x", _at(10), "A"),
        _prog("x", _at(12), "C", stop=_at(13)),
        _prog("y", _at(10), "B"),
        _prog("x", _at(12), "C", stop=_at(13)),  # exact duplicate
    ]
    expected = [
        ("y", "Morgen", _at(9), _at(10)),
        ("x", "A", _at(10), _at(12)),
        ("x", "B", _at(10), _at(12)),
        ("y", "B", _at(10), _at(11)),
        ("x", "C", _at(12), _at(13)),
    ]
    for seed in range(10):
        shuffled = programmes.copy()
        random.Random(seed).shuffle(shuffled)  # noqa: S311 - deterministic test shuffle, not crypto
        result, _ = _normalize(shuffled)
        assert _spans(result) == expected, f"seed {seed}"


def test_empty_input() -> None:
    result, stats = _normalize([])
    assert result == ()
    assert stats.inferred_stops == 0
    assert stats.duplicates == 0
