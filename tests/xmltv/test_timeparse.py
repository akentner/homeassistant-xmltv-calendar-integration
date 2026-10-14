"""Table test for every XMLTV timestamp variant (EVT-05, D-14)."""

from datetime import UTC, datetime

import pytest

from custom_components.xmltv_calendar.xmltv.timeparse import parse_xmltv_time


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
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
    ],
)
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
