"""
Pure schedule tables: daily slots across DST, freshness, backoff, persistent failure, stored options (SRC-05, D-06).

Functions are looked up on the module inside each test, so a missing name fails its own rows, not the import.
"""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.xmltv_calendar.xmltv import schedule as S  # noqa: N812

BERLIN = ZoneInfo("Europe/Berlin")


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(UTC)


def _daily(at: str = "18:15", tz=BERLIN) -> S.Schedule:
    return S.Schedule(interval=None, daily_at=time.fromisoformat(at), tz=tz)


def _interval(hours: int = 24) -> S.Schedule:
    return S.Schedule(interval=timedelta(hours=hours), daily_at=None, tz=BERLIN)


def _assert_utc(value: datetime) -> None:
    assert value.tzinfo is UTC


# ---- daily slots ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("now", "at", "tz", "expected"),
    [
        pytest.param("2026-10-13T16:00:00Z", "18:15", BERLIN, "2026-10-13T16:15:00Z", id="before-slot"),
        pytest.param("2026-10-13T16:15:00Z", "18:15", BERLIN, "2026-10-14T16:15:00Z", id="at-slot-strictly-after"),
        pytest.param("2026-10-24T17:00:00Z", "18:15", BERLIN, "2026-10-25T17:15:00Z", id="dst-end-2026-10-25"),
        # 18:00Z is 19:00 CET on 2026-03-28, after that day's slot; the next one is already CEST
        pytest.param("2026-03-28T18:00:00Z", "18:15", BERLIN, "2026-03-29T16:15:00Z", id="dst-start-2026-03-29"),
        pytest.param("2026-03-28T17:00:00Z", "18:15", BERLIN, "2026-03-28T17:15:00Z", id="eve-of-dst-start-cet"),
        pytest.param("2026-03-28T23:00:00Z", "02:30", BERLIN, "2026-03-29T01:30:00Z", id="gap-2026-03-29-0230"),
        pytest.param("2026-10-24T23:00:00Z", "02:30", BERLIN, "2026-10-25T00:30:00Z", id="fold-2026-10-25-0230"),
        pytest.param("2026-10-13T23:59:59Z", "00:00", UTC, "2026-10-14T00:00:00Z", id="utc-midnight"),
    ],
)
def test_next_slot(now: str, at: str, tz, expected: str) -> None:
    result = S.next_slot(_utc(now), _daily(at, tz))
    assert result == _utc(expected)
    _assert_utc(result)


@pytest.mark.parametrize(
    ("now", "at", "expected"),
    [
        pytest.param("2026-10-13T16:15:00Z", "18:15", "2026-10-13T16:15:00Z", id="at-slot-inclusive"),
        pytest.param("2026-10-13T16:14:59Z", "18:15", "2026-10-12T16:15:00Z", id="just-before-slot"),
        pytest.param("2026-10-25T17:00:00Z", "18:15", "2026-10-24T16:15:00Z", id="dst-end-2026-10-25"),
        pytest.param("2026-03-29T17:00:00Z", "18:15", "2026-03-29T16:15:00Z", id="dst-start-2026-03-29"),
        pytest.param("2026-03-29T02:00:00Z", "02:30", "2026-03-29T01:30:00Z", id="gap-2026-03-29-0230"),
        pytest.param("2026-10-25T02:00:00Z", "02:30", "2026-10-25T00:30:00Z", id="fold-2026-10-25-0230"),
    ],
)
def test_last_slot(now: str, at: str, expected: str) -> None:
    result = S.last_slot(_utc(now), _daily(at))
    assert result == _utc(expected)
    _assert_utc(result)


@pytest.mark.parametrize("name", ["last_slot", "next_slot"])
def test_slots_need_a_daily_schedule(name: str) -> None:
    with pytest.raises(ValueError, match="daily"):
        getattr(S, name)(_utc("2026-10-13T06:00:00Z"), _interval())


# ---- freshness and regular targets -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fetched_at", "now", "schedule", "expected"),
    [
        pytest.param("2026-10-12T06:00:01Z", "2026-10-13T06:00:00Z", _interval(), True, id="interval-fresh"),
        pytest.param("2026-10-12T06:00:00Z", "2026-10-13T06:00:00Z", _interval(), False, id="interval-age-equals"),
        pytest.param("2026-10-13T16:15:00Z", "2026-10-14T16:14:00Z", _daily(), True, id="daily-before-next-slot"),
        pytest.param("2026-10-13T16:15:00Z", "2026-10-14T16:15:00Z", _daily(), False, id="daily-missed-slot"),
        pytest.param("2026-10-13T16:14:00Z", "2026-10-13T17:00:00Z", _daily(), False, id="daily-fetched-before-slot"),
        pytest.param("2026-10-13T06:01:00Z", "2026-10-13T06:00:00Z", _interval(), False, id="interval-future-fetch"),
        pytest.param("2026-10-13T06:01:00Z", "2026-10-13T06:00:00Z", _daily(), False, id="daily-future-fetch"),
    ],
)
def test_is_fresh(fetched_at: str, now: str, schedule: S.Schedule, expected: bool) -> None:
    assert S.is_fresh(_utc(fetched_at), _utc(now), schedule) is expected


def test_fresh_until_interval() -> None:
    fetched_at = _utc("2026-10-13T05:00:00Z")
    result = S.fresh_until(fetched_at, _utc("2026-10-13T06:00:00Z"), _interval(24))
    assert result == _utc("2026-10-14T05:00:00Z")
    _assert_utc(result)


def test_fresh_until_daily() -> None:
    now = _utc("2026-10-13T17:00:00Z")
    result = S.fresh_until(_utc("2026-10-13T16:20:00Z"), now, _daily())
    assert result == S.next_slot(now, _daily()) == _utc("2026-10-14T16:15:00Z")
    _assert_utc(result)


def test_next_regular_interval() -> None:
    result = S.next_regular(_utc("2026-10-13T06:00:00Z"), _interval(2))
    assert result == _utc("2026-10-13T08:00:00Z")
    _assert_utc(result)


def test_next_regular_daily() -> None:
    now = _utc("2026-10-13T16:00:00Z")
    assert S.next_regular(now, _daily()) == S.next_slot(now, _daily()) == _utc("2026-10-13T16:15:00Z")


# ---- backoff (D-10) ------------------------------------------------------------------------------------------------

NOW = _utc("2026-10-13T06:00:00Z")


def test_backoff_steps() -> None:
    assert (
        timedelta(minutes=5),
        timedelta(minutes=15),
        timedelta(hours=1),
        timedelta(hours=3),
        timedelta(hours=6),
    ) == S.BACKOFF_STEPS


@pytest.mark.parametrize(
    ("failures", "regular_in", "expected"),
    [
        pytest.param(1, timedelta(hours=24), timedelta(minutes=5), id="1st"),
        pytest.param(2, timedelta(hours=24), timedelta(minutes=15), id="2nd"),
        pytest.param(3, timedelta(hours=24), timedelta(hours=1), id="3rd"),
        pytest.param(4, timedelta(hours=24), timedelta(hours=3), id="4th"),
        pytest.param(5, timedelta(hours=24), timedelta(hours=6), id="5th"),
        pytest.param(6, timedelta(hours=24), timedelta(hours=6), id="6th"),
        pytest.param(7, timedelta(hours=24), timedelta(hours=6), id="7th"),
        pytest.param(4, timedelta(hours=2), timedelta(hours=2), id="capped-4th"),
        pytest.param(5, timedelta(hours=2), timedelta(hours=2), id="capped-5th"),
        pytest.param(2, timedelta(minutes=10), timedelta(minutes=10), id="capped-2nd"),
        pytest.param(1, timedelta(0), timedelta(seconds=1), id="regular-now"),
        pytest.param(3, timedelta(minutes=-5), timedelta(seconds=1), id="regular-past"),
        pytest.param(0, timedelta(hours=24), timedelta(minutes=5), id="zero-failures"),
        pytest.param(-3, timedelta(hours=24), timedelta(minutes=5), id="negative-failures"),
    ],
)
def test_backoff_delay(failures: int, regular_in: timedelta, expected: timedelta) -> None:
    assert S.backoff_delay(failures, NOW, NOW + regular_in) == expected


# ---- refresh base (CR-01: a timer that fires just before its target serves it) -------------------------------------


@pytest.mark.parametrize(
    ("now", "target", "expected"),
    [
        pytest.param("2026-10-13T16:15:01Z", "2026-10-13T16:15:00Z", "2026-10-13T16:15:01Z", id="late-fire"),
        pytest.param("2026-10-13T16:15:00Z", "2026-10-13T16:15:00Z", "2026-10-13T16:15:00Z", id="on-time"),
        pytest.param("2026-10-13T16:14:59.400Z", "2026-10-13T16:15:00Z", "2026-10-13T16:15:00Z", id="early-fire"),
        pytest.param("2026-10-13T16:14:58Z", "2026-10-13T16:15:00Z", "2026-10-13T16:15:00Z", id="at-tolerance"),
        pytest.param(
            "2026-10-13T16:14:57.999Z", "2026-10-13T16:15:00Z", "2026-10-13T16:14:57.999Z", id="beyond-tolerance"
        ),
        pytest.param("2026-10-13T16:10:00Z", "2026-10-13T16:15:00Z", "2026-10-13T16:10:00Z", id="manual-before-slot"),
    ],
)
def test_refresh_base(now: str, target: str, expected: str) -> None:
    assert S.refresh_base(_utc(now), _utc(target)) == _utc(expected)


def test_early_fire_tolerance() -> None:
    assert timedelta(seconds=2) == S.EARLY_FIRE_TOLERANCE
    assert S.EARLY_FIRE_TOLERANCE >= S.MIN_DELAY


def test_early_fire_serves_daily_slot() -> None:
    slot = _utc("2026-10-13T16:15:00Z")
    assert S.next_regular(S.refresh_base(_utc("2026-10-13T16:14:59.400Z"), slot), _daily()) == _utc(
        "2026-10-14T16:15:00Z"
    )
    assert S.next_regular(S.refresh_base(_utc("2026-10-13T16:10:00Z"), slot), _daily()) == slot


# ---- persistent failure (D-17, measured from failing_since) ---------------------------------------------------------


@pytest.mark.parametrize(
    ("failing_since", "expected"),
    [
        pytest.param(None, False, id="not-failing"),
        pytest.param(NOW - timedelta(hours=24), False, id="exactly-24h"),
        pytest.param(NOW - timedelta(hours=24, seconds=1), True, id="over-24h"),
        pytest.param(NOW - timedelta(hours=1), False, id="1h"),
        pytest.param(NOW + timedelta(hours=30), False, id="future"),
    ],
)
def test_is_persistently_failing(failing_since: datetime | None, expected: bool) -> None:
    assert S.is_persistently_failing(failing_since, NOW) is expected


def test_persistent_failure_threshold() -> None:
    assert timedelta(hours=24) == S.PERSISTENT_FAILURE


# ---- stored source options (D-06) -----------------------------------------------------------------------------------


def test_from_empty_mapping() -> None:
    options = S.SourceOptions.from_mapping({})
    assert options.refresh_mode == S.REFRESH_MODE_INTERVAL
    assert options.refresh_hours == S.DEFAULT_REFRESH_HOURS == 24
    assert options.refresh_time is None
    assert options.naive_timezone == S.NAIVE_TZ_UTC
    assert options.offset_minutes == S.DEFAULT_OFFSET_MINUTES == 0
    assert options.as_options() == {
        S.KEY_REFRESH_MODE: S.REFRESH_MODE_INTERVAL,
        S.KEY_REFRESH_HOURS: 24,
        S.KEY_NAIVE_TIMEZONE: S.NAIVE_TZ_UTC,
        S.KEY_OFFSET_MINUTES: 0,
    }


def test_phase1_entry() -> None:
    options = S.SourceOptions.from_mapping({S.KEY_REFRESH_HOURS: 12})
    assert (options.refresh_mode, options.refresh_hours) == (S.REFRESH_MODE_INTERVAL, 12)


def test_daily_with_seconds() -> None:
    options = S.SourceOptions.from_mapping({S.KEY_REFRESH_MODE: S.REFRESH_MODE_DAILY, S.KEY_REFRESH_TIME: "18:15:00"})
    assert (options.refresh_mode, options.refresh_time) == (S.REFRESH_MODE_DAILY, "18:15")
    assert options.as_options()[S.KEY_REFRESH_TIME] == "18:15"


@pytest.mark.parametrize(
    "mapping",
    [
        pytest.param(lambda: {S.KEY_REFRESH_MODE: S.REFRESH_MODE_DAILY}, id="daily-without-time"),
        pytest.param(lambda: {S.KEY_REFRESH_MODE: S.REFRESH_MODE_DAILY, S.KEY_REFRESH_TIME: "25:00"}, id="bad-time"),
        pytest.param(lambda: {S.KEY_REFRESH_MODE: "weekly"}, id="unknown-mode"),
    ],
)
def test_invalid_daily_falls_back_to_interval(mapping) -> None:
    options = S.SourceOptions.from_mapping(mapping())
    assert options.refresh_mode == S.REFRESH_MODE_INTERVAL
    assert options.refresh_time is None
    assert S.KEY_REFRESH_TIME not in options.as_options()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(0, 1, id="zero"),
        pytest.param(500, 168, id="too-large"),
        pytest.param("abc", 24, id="text"),
        pytest.param(True, 24, id="bool"),
        pytest.param(12.0, 12, id="integral-float"),
        pytest.param(12.5, 24, id="fraction"),
    ],
)
def test_refresh_hours_read(raw: object, expected: int) -> None:
    assert S.SourceOptions.from_mapping({S.KEY_REFRESH_HOURS: raw}).refresh_hours == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(900, 720, id="too-large"),
        pytest.param(-900, -720, id="too-small"),
        pytest.param("x", 0, id="text"),
        pytest.param(True, 0, id="bool"),
        pytest.param(30.0, 30, id="integral-float"),
        pytest.param(30.5, 0, id="fraction"),
        pytest.param(-90, -90, id="negative-in-range"),
    ],
)
def test_offset_minutes_read(raw: object, expected: int) -> None:
    assert S.SourceOptions.from_mapping({S.KEY_OFFSET_MINUTES: raw}).offset_minutes == expected


def test_offset_range() -> None:
    assert (S.MIN_OFFSET_MINUTES, S.MAX_OFFSET_MINUTES) == (-720, 720)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(lambda: S.NAIVE_TZ_LOCAL, lambda: S.NAIVE_TZ_LOCAL, id="local"),
        pytest.param(lambda: S.NAIVE_TZ_UTC, lambda: S.NAIVE_TZ_UTC, id="utc"),
        pytest.param(lambda: "berlin", lambda: S.NAIVE_TZ_UTC, id="unknown"),
    ],
)
def test_naive_timezone_read(raw, expected) -> None:
    assert S.SourceOptions.from_mapping({S.KEY_NAIVE_TIMEZONE: raw()}).naive_timezone == expected()
    assert S.NAIVE_TIMEZONES == (S.NAIVE_TZ_UTC, S.NAIVE_TZ_LOCAL)


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(S.SourceOptions, id="defaults"),
        pytest.param(lambda: S.SourceOptions(refresh_hours=1), id="hourly"),
        pytest.param(
            lambda: S.SourceOptions(refresh_mode=S.REFRESH_MODE_DAILY, refresh_time="18:15"),
            id="daily",
        ),
        pytest.param(
            lambda: S.SourceOptions(naive_timezone=S.NAIVE_TZ_LOCAL, offset_minutes=-720, refresh_hours=168),
            id="local-offset",
        ),
        pytest.param(
            lambda: S.SourceOptions(
                refresh_mode=S.REFRESH_MODE_DAILY, refresh_time="00:00", naive_timezone=S.NAIVE_TZ_LOCAL
            ),
            id="daily-local",
        ),
    ],
)
def test_options_round_trip(build) -> None:
    options = build()
    assert S.SourceOptions.from_mapping(options.as_options()) == options


@pytest.mark.parametrize("bad", [None, [], {}, True, [1, 2], {"a": 1}, b"18:15"])
def test_from_mapping_never_raises(bad: object) -> None:
    keys = (S.KEY_REFRESH_MODE, S.KEY_REFRESH_HOURS, S.KEY_REFRESH_TIME, S.KEY_NAIVE_TIMEZONE, S.KEY_OFFSET_MINUTES)
    options = S.SourceOptions.from_mapping(dict.fromkeys(keys, bad))
    assert options == S.SourceOptions()
    assert options.refresh_mode in S.REFRESH_MODES


def test_schedule_from_options() -> None:
    interval = S.SourceOptions(refresh_hours=6).schedule(BERLIN)
    assert interval == S.Schedule(interval=timedelta(hours=6), daily_at=None, tz=BERLIN)
    daily = S.SourceOptions(refresh_mode=S.REFRESH_MODE_DAILY, refresh_time="18:15").schedule(BERLIN)
    assert daily == S.Schedule(interval=None, daily_at=time(18, 15), tz=BERLIN)
