"""Table test for every XMLTV timestamp variant (EVT-05, D-14) and the naive-timezone option (SRC-10)."""

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from custom_components.xmltv_calendar.xmltv.timeparse import parse_xmltv_time


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


BERLIN = ZoneInfo("Europe/Berlin")

VALID = [
    ("20261012203000 +0200", _utc(2026, 10, 12, 18, 30)),
    ("202610122030 +0200", _utc(2026, 10, 12, 18, 30)),  # 12-digit, not 20:03
    ("20261012203000 +02:00", _utc(2026, 10, 12, 18, 30)),
    ("20261012203000+0200", _utc(2026, 10, 12, 18, 30)),
    ("20261012203000 -0130", _utc(2026, 10, 12, 22, 0)),
    ("20261012203000", _utc(2026, 10, 12, 20, 30)),  # D-14: no offset means UTC
    ("20261012203000 Z", _utc(2026, 10, 12, 20, 30)),
    ("20261012203000 UTC", _utc(2026, 10, 12, 20, 30)),
    ("20261012203000 GMT", _utc(2026, 10, 12, 20, 30)),
    ("20261012203000 BST", _utc(2026, 10, 12, 19, 30)),
    ("20261012203000 CET", _utc(2026, 10, 12, 19, 30)),
    ("20261012203000 CEST", _utc(2026, 10, 12, 18, 30)),
    ("20261012203000 EET", _utc(2026, 10, 12, 18, 30)),
    ("20261012203000 EEST", _utc(2026, 10, 12, 17, 30)),
    # DST nights with explicit offsets
    ("20261025023000 +0200", _utc(2026, 10, 25, 0, 30)),
    ("20261025023000 +0100", _utc(2026, 10, 25, 1, 30)),
    ("20260329030000 +0200", _utc(2026, 3, 29, 1, 0)),
    # CR-01: 18 h is the largest accepted offset, the year window 1900..2200 is inclusive
    ("20261012203000 +1800", _utc(2026, 10, 12, 2, 30)),
    ("20261012203000 -1800", _utc(2026, 10, 13, 14, 30)),
    ("19000101000000 +0000", _utc(1900, 1, 1, 0, 0)),
    ("22001231235959 +0000", _utc(2200, 12, 31, 23, 59, 59)),
]


@pytest.mark.parametrize(("value", "expected"), VALID)
def test_valid_timestamps(value: str, expected: datetime) -> None:
    result = parse_xmltv_time(value)
    assert result is not None
    assert result.tzinfo is not None
    assert result == expected
    assert result.astimezone(UTC) == expected


@pytest.mark.parametrize(
    "value",
    [
        "20261012203000 XYZ",  # unknown alpha zone
        "garbage",
        "",
        None,
        "20261332000000 +0000",  # month 13
        "20261012253000 +0000",  # hour 25
        # CR-01: out-of-range offsets and years
        "20261012203000 +2500",
        "20261012203000 -2500",
        "20261012203000 +1801",
        "20261012203000 +0099",
        "20261012203000 +01:60",
        "00010101000000 +0100",
        "99991231233000 -0100",
        "99991231233000 +0000",
        "18991231235959 +0000",
        "22010101000000 +0000",
    ],
)
def test_invalid_timestamps_return_none(value: str | None) -> None:
    assert parse_xmltv_time(value) is None


@pytest.mark.parametrize(("value", "expected"), VALID)
def test_default_arguments_unchanged(value: str, expected: datetime) -> None:
    default = parse_xmltv_time(value)
    explicit = parse_xmltv_time(value, UTC)
    assert default == explicit == expected
    assert default is not None
    assert explicit is not None
    assert default.tzinfo is explicit.tzinfo
    assert default.utcoffset() == explicit.utcoffset()


def test_naive_timestamp_keeps_utc_tzinfo_by_default() -> None:
    result = parse_xmltv_time("20261012203000")
    assert result is not None
    assert result.tzinfo is UTC


@pytest.mark.parametrize(
    ("value", "expected", "offset_hours"),
    [
        pytest.param("20261013200000", _utc(2026, 10, 13, 18), 2, id="summer-2026-10-13"),
        pytest.param("20261215200000", _utc(2026, 12, 15, 19), 1, id="winter-2026-12-15"),
        pytest.param("202610132000", _utc(2026, 10, 13, 18), 2, id="no-seconds-2026-10-13"),
        pytest.param("20261013", _utc(2026, 10, 12, 22), 2, id="date-only-2026-10-13"),
        pytest.param("20260329023000", _utc(2026, 3, 29, 1, 30), 1, id="gap-2026-03-29"),
        pytest.param("20261025023000", _utc(2026, 10, 25, 0, 30), 2, id="fold-first-2026-10-25"),
        pytest.param("20261025013000", _utc(2026, 10, 24, 23, 30), 2, id="before-fold-2026-10-25"),
        pytest.param("20261025033000", _utc(2026, 10, 25, 2, 30), 1, id="after-fold-2026-10-25"),
    ],
)
def test_naive_local_timestamps(value: str, expected: datetime, offset_hours: int) -> None:
    result = parse_xmltv_time(value, BERLIN)
    assert result is not None
    assert result == expected
    assert result.utcoffset() == timedelta(hours=offset_hours)
    # Fixed offset, never a ZoneInfo: datetime arithmetic on the result stays absolute across DST
    assert type(result.tzinfo) is timezone


def test_naive_local_results_share_cached_offsets() -> None:
    first = parse_xmltv_time("20261013200000", BERLIN)
    second = parse_xmltv_time("20261014090000", BERLIN)
    explicit = parse_xmltv_time("20261013200000 +0200")
    assert first is not None
    assert second is not None
    assert explicit is not None
    assert first.tzinfo is second.tzinfo is explicit.tzinfo


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("20261013200000 +0000", _utc(2026, 10, 13, 20), id="numeric-zero-2026-10-13"),
        pytest.param("20261013200000 UTC", _utc(2026, 10, 13, 20), id="alpha-utc-2026-10-13"),
        pytest.param("20261013200000 +0200", _utc(2026, 10, 13, 18), id="numeric-2026-10-13"),
        pytest.param("20261025023000 +0100", _utc(2026, 10, 25, 1, 30), id="numeric-fold-2026-10-25"),
        pytest.param("20260329023000 CET", _utc(2026, 3, 29, 1, 30), id="alpha-gap-2026-03-29"),
    ],
)
def test_explicit_zones_ignore_naive_timezone(value: str, expected: datetime) -> None:
    assert parse_xmltv_time(value, BERLIN) == expected


@pytest.mark.parametrize("value", ["garbage", "20261332000000", "18991231235959", "22010101000000", None])
def test_naive_local_invalid_timestamps_return_none(value: str | None) -> None:
    assert parse_xmltv_time(value, BERLIN) is None
