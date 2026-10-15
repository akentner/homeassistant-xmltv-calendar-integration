"""Filter engine truth table: channel AND (include empty OR any include) AND NOT any exclude (D-02 to D-08)."""

import unicodedata
from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from custom_components.xmltv_calendar.xmltv import filter as filter_module
from custom_components.xmltv_calendar.xmltv.filter import (
    FilterSpec,
    InvalidPattern,
    first_invalid_pattern,
    has_nested_repeat,
)
from custom_components.xmltv_calendar.xmltv.model import Channel, EpgData, ParseStats, Programme
from custom_components.xmltv_calendar.xmltv.settings import (
    FIELD_CATEGORY,
    FIELD_DESCRIPTION,
    FIELD_SUBTITLE,
    FIELD_TITLE,
    KEY_CASE_SENSITIVE,
    KEY_CHANNEL_REGEX,
    KEY_CHANNELS,
    KEY_EXCLUDE,
    KEY_EXCLUDE_FIELDS,
    KEY_INCLUDE,
    KEY_INCLUDE_FIELDS,
    KEY_MAX_DURATION,
    KEY_MIN_DURATION,
    KEY_TIME_FROM,
    KEY_TIME_TO,
    KEY_WEEKDAYS,
)

BASE = datetime(2026, 10, 13, 8, tzinfo=UTC)
# Caps from the plan (T-01-06); literals so this module still collects before the constants exist
MAX_PATTERN_LENGTH = 300
MAX_PATTERN_LINES = 50


def _prog(index: int, channel: str, title: str, sub_title: str | None = None) -> Programme:
    start = BASE + timedelta(hours=index)
    return Programme(
        channel_id=channel,
        start=start,
        stop=start + timedelta(minutes=30),
        titles=(title,),
        sub_titles=(sub_title,) if sub_title else (),
        description=None,
        categories=(),
        episode=None,
    )


P1 = _prog(1, "daserste.de", "Tagesschau")
P2 = _prog(2, "daserste.de", "Tagesschau extra")
P3 = _prog(3, "zdf.de", "Tatort", "Der Fall")
P4 = _prog(4, "zdf.de", "Tatort: Der Fall")
P5 = _prog(5, "sky.de", "Formel 1: Rennen", "Live")
P6 = _prog(6, "sky.de", "formula 1 highlights")
P7 = _prog(7, "one.de", "Großer Preis")
ALL = (P1, P2, P3, P4, P5, P6, P7)

# one.de has programmes but no <channel> element, as in real feeds that omit channel metadata
EPG = EpgData(
    channels={cid: Channel(id=cid, display_name=cid) for cid in ("daserste.de", "zdf.de", "sky.de")},
    programmes=ALL,
    stats=ParseStats(),
)


def _apply(data: dict[str, Any]) -> tuple[Programme, ...]:
    return FilterSpec.from_mapping(data).apply(EPG).matches


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param({"include": "^Tagesschau$"}, (P1,), id="anchored-include"),
        pytest.param({"include": "tagesschau"}, (P1, P2), id="case-insensitive-include"),
        pytest.param({"include": "^Tatort$"}, (P3,), id="title-matched-alone"),
        pytest.param({"include": "^Der Fall$"}, (P3,), id="sub-title-match"),
        pytest.param({"include": r"formel\s*1|formula\s*1"}, (P5, P6), id="alternation"),
        pytest.param({"include": "tatort", "exclude": "Der Fall"}, (), id="exclude-on-title-and-sub-title"),
        pytest.param({"include": "", "exclude": ""}, ALL, id="empty-include-and-exclude"),
        pytest.param({"include": "\n  \n"}, ALL, id="blank-include-lines"),
        pytest.param({"exclude": "  \n\t\n"}, ALL, id="blank-exclude-lines-exclude-nothing"),
        pytest.param({"exclude": "^Live$"}, (P1, P2, P3, P4, P6, P7), id="exclude-sub-title"),
        pytest.param({"include": "groß"}, (P7,), id="literal-umlaut"),
        pytest.param({"include": "tagesschau\nformel"}, (P1, P2, P5), id="include-lines-or-combined"),
        pytest.param({"channels": ["zdf.de"]}, (P3, P4), id="selected-channel"),
        pytest.param({"channel_regex": "^sky"}, (P5, P6), id="channel-regex"),
        pytest.param({"channels": ["zdf.de"], "channel_regex": "^z"}, (P3, P4), id="selected-and-regex-same-channel"),
        pytest.param({"channels": ["gone.de", "zdf.de"]}, (P3, P4), id="missing-channel-ignored"),
        pytest.param({"channels": [], "channel_regex": ""}, ALL, id="no-channel-filter"),
        pytest.param({}, ALL, id="empty-mapping"),
    ],
)
def test_truth_table(data: dict[str, Any], expected: tuple[Programme, ...]) -> None:
    assert _apply(data) == expected


def test_exclude_removes_matches() -> None:
    # P3 is excluded by its sub-title, P4 by its title
    assert _apply({"include": "tatort", "exclude": "Der Fall"}) == ()


def test_channel_regex_selects_by_id() -> None:
    assert _apply({"channel_regex": "^sky"}) == (P5, P6)


def test_selected_and_regex_channel_counted_once() -> None:
    matches = _apply({"channels": ["zdf.de"], "channel_regex": "^(z|sky)"})
    assert matches == (P3, P4, P5, P6)
    assert set(Counter(matches).values()) == {1}


def test_missing_channels_reported() -> None:
    # gone.de is absent everywhere; one.de has programmes but no <channel> element, so it is not missing
    result = FilterSpec.from_mapping({"channels": ["gone.de", "one.de"]}).apply(EPG)
    assert result.matches == (P7,)
    assert result.missing_channels == frozenset({"gone.de"})


def test_first_invalid_pattern_caps() -> None:
    too_long = "a" * (MAX_PATTERN_LENGTH + 1)
    too_long_result = first_invalid_pattern(too_long)
    assert too_long_result is not None
    assert too_long_result.pattern == too_long

    lines = [f"p{i}" for i in range(MAX_PATTERN_LINES + 1)]
    too_many_result = first_invalid_pattern("\n".join(lines))
    assert too_many_result is not None
    assert too_many_result.pattern == lines[MAX_PATTERN_LINES]


def test_first_invalid_pattern_reports_compile_error() -> None:
    result = first_invalid_pattern("ok\n(")
    assert result is not None
    assert result.pattern == "("
    assert result.message


@pytest.mark.parametrize("text", ["", "a\n\nb", "\n".join(f"p{i}" for i in range(MAX_PATTERN_LINES)), "a" * 300])
def test_first_invalid_pattern_accepts_valid_input(text: str) -> None:
    assert first_invalid_pattern(text) is None


# Phase 2 field selection and case table (D-05, D-07, D-08)
def _q(
    index: int,
    channel: str,
    title: str,
    *,
    sub_titles: tuple[str, ...] = (),
    description: str | None = None,
    categories: tuple[str, ...] = (),
) -> Programme:
    start = BASE + timedelta(hours=index)
    return Programme(
        channel_id=channel,
        start=start,
        stop=start + timedelta(minutes=30),
        titles=(title,),
        sub_titles=sub_titles,
        description=description,
        categories=categories,
        episode=None,
    )


Q1 = _q(1, "daserste.de", "Sportschau", categories=("Sport",))
Q2 = _q(2, "daserste.de", "Tagesschau", categories=("News", "Sport"), description="Mit Wiederholung")
Q3 = _q(3, "zdf.de", "Sport extra", categories=("Sportnachrichten",))
Q4 = _q(4, "zdf.de", "Tatort", sub_titles=("Der Fall", "Teil 2"))
Q_ALL = (Q1, Q2, Q3, Q4)
Q_EPG = EpgData(
    channels={cid: Channel(id=cid, display_name=cid) for cid in ("daserste.de", "zdf.de")},
    programmes=Q_ALL,
    stats=ParseStats(),
)


def _q_apply(data: dict[str, Any]) -> tuple[Programme, ...]:
    return FilterSpec.from_mapping(data).apply(Q_EPG).matches


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param({KEY_INCLUDE: "^Sport$", KEY_INCLUDE_FIELDS: [FIELD_CATEGORY]}, (Q1, Q2), id="category-element"),
        pytest.param({KEY_INCLUDE: "^Sport", KEY_INCLUDE_FIELDS: [FIELD_TITLE]}, (Q1, Q3), id="title-only"),
        pytest.param({KEY_INCLUDE: "^Teil 2$", KEY_INCLUDE_FIELDS: [FIELD_SUBTITLE]}, (Q4,), id="second-sub-title"),
        pytest.param(
            {
                KEY_INCLUDE: "schau",
                KEY_INCLUDE_FIELDS: [FIELD_TITLE],
                KEY_EXCLUDE: "Wiederholung",
                KEY_EXCLUDE_FIELDS: [FIELD_DESCRIPTION],
            },
            (Q1,),
            id="independent-include-exclude-fields",
        ),
        pytest.param({KEY_INCLUDE: "wiederholung"}, (), id="default-fields-skip-description"),
        pytest.param(
            {KEY_INCLUDE: "wiederholung", KEY_INCLUDE_FIELDS: [FIELD_DESCRIPTION]}, (Q2,), id="description-only"
        ),
        pytest.param({KEY_INCLUDE: "x", KEY_INCLUDE_FIELDS: [FIELD_DESCRIPTION]}, (), id="missing-description"),
        pytest.param({KEY_INCLUDE: ".", KEY_INCLUDE_FIELDS: [FIELD_SUBTITLE]}, (Q4,), id="missing-sub-titles"),
        pytest.param({KEY_INCLUDE: "tagesschau", KEY_CASE_SENSITIVE: True}, (), id="case-sensitive-lowercase-misses"),
        pytest.param({KEY_INCLUDE: "Tagesschau", KEY_CASE_SENSITIVE: True}, (Q2,), id="case-sensitive-exact"),
        pytest.param({KEY_EXCLUDE: "tatort", KEY_CASE_SENSITIVE: True}, Q_ALL, id="case-sensitive-exclude"),
        pytest.param({KEY_INCLUDE: "\n \n", KEY_CASE_SENSITIVE: True}, Q_ALL, id="case-sensitive-blank-lines"),
        pytest.param(
            {KEY_CHANNEL_REGEX: "^DASERSTE", KEY_CASE_SENSITIVE: True}, (Q1, Q2), id="channel-regex-stays-insensitive"
        ),
    ],
)
def test_field_and_case_table(data: dict[str, Any], expected: tuple[Programme, ...]) -> None:
    assert _q_apply(data) == expected


def test_field_selection_does_not_leak_between_specs() -> None:
    by_title = FilterSpec.from_mapping({KEY_INCLUDE: "sport", KEY_INCLUDE_FIELDS: [FIELD_TITLE]})
    by_category = FilterSpec.from_mapping({KEY_INCLUDE: "sport", KEY_INCLUDE_FIELDS: [FIELD_CATEGORY]})
    sensitive = FilterSpec.from_mapping({KEY_INCLUDE: "sport", KEY_CASE_SENSITIVE: True})

    assert by_title.apply(Q_EPG).matches == (Q1, Q3)
    assert by_category.apply(Q_EPG).matches == (Q1, Q2, Q3)
    assert sensitive.apply(Q_EPG).matches == ()
    assert by_title.apply(Q_EPG).matches == (Q1, Q3)


def test_filter_apply_is_deterministic() -> None:
    spec = FilterSpec.from_mapping(
        {KEY_INCLUDE: "sport|teil", KEY_INCLUDE_FIELDS: [FIELD_CATEGORY, FIELD_SUBTITLE], KEY_CASE_SENSITIVE: False}
    )

    first = spec.apply(Q_EPG)
    second = spec.apply(Q_EPG)

    assert first == second
    assert first.matches == (Q1, Q2, Q3, Q4)


# Unicode: NFC code-point equality, never case-folded (D-08, Pitfall 4)
U1 = _q(1, "a.de", "Strasse")
U2 = _q(2, "a.de", "Straße")
U3 = _q(3, "a.de", "Tatort Köln")
U4 = _q(4, "a.de", "Ab 12")
U_EPG = EpgData(
    channels={"a.de": Channel(id="a.de", display_name="A")}, programmes=(U1, U2, U3, U4), stats=ParseStats()
)


@pytest.mark.parametrize(
    ("include", "expected"),
    [
        pytest.param("stra(ß|ss)e", (U1, U2), id="sharp-s-alternation"),
        pytest.param("straße", (U2,), id="sharp-s-is-not-ss"),
        pytest.param(unicodedata.normalize("NFD", "köln"), (U3,), id="nfd-pattern"),
        pytest.param(unicodedata.normalize("NFD", "[äöü]ln"), (U3,), id="nfd-character-class"),
        pytest.param(r"^\S+ \d+$", (U4,), id="escapes-keep-meaning"),
    ],
)
def test_unicode_matching(include: str, expected: tuple[Programme, ...]) -> None:
    assert FilterSpec.from_mapping({KEY_INCLUDE: include}).apply(U_EPG).matches == expected


# --- Time window, weekdays and duration (FLT-08, FLT-09, D-09 to D-14) ---------------------------------------------

BERLIN = ZoneInfo("Europe/Berlin")
CEST = timezone(timedelta(hours=2))  # the parser's cached fixed offsets
CET = timezone(timedelta(hours=1))


def _timed(
    start: datetime,
    stop: datetime | None = None,
    *,
    channel: str = "ch.de",
    title: str = "Show",
) -> Programme:
    return Programme(
        channel_id=channel,
        start=start,
        stop=stop if stop is not None else start + timedelta(minutes=30),
        titles=(title,),
        sub_titles=(),
        description=None,
        categories=(),
        episode=None,
    )


def _timed_epg(*programmes: Programme) -> EpgData:
    return EpgData(channels={}, programmes=programmes, stats=ParseStats())


def _passes(data: dict[str, Any], programme: Programme) -> bool:
    return FilterSpec.from_mapping(data).apply(_timed_epg(programme), tz=BERLIN).matches == (programme,)


FRIDAY_NIGHT = {KEY_TIME_FROM: "22:00", KEY_TIME_TO: "02:00", KEY_WEEKDAYS: ["fri"]}
MORNING = {KEY_TIME_FROM: "06:00", KEY_TIME_TO: "09:00"}
WEEKEND = {KEY_WEEKDAYS: ["sat", "sun"]}
SATURDAY_LATE = {KEY_TIME_FROM: "22:00", KEY_TIME_TO: "04:00", KEY_WEEKDAYS: ["sat"]}


@pytest.mark.parametrize(
    ("data", "start", "expected"),
    [
        # D-11: midnight-crossing window anchored to the day it opened on; half-open end (A2)
        pytest.param(FRIDAY_NIGHT, datetime(2026, 10, 16, 22, tzinfo=CEST), True, id="fri-night-fri-22:00"),
        pytest.param(FRIDAY_NIGHT, datetime(2026, 10, 17, 1, tzinfo=CEST), True, id="fri-night-sat-01:00"),
        pytest.param(FRIDAY_NIGHT, datetime(2026, 10, 17, 1, 59, tzinfo=CEST), True, id="fri-night-sat-01:59"),
        pytest.param(FRIDAY_NIGHT, datetime(2026, 10, 16, 1, tzinfo=CEST), False, id="fri-night-fri-01:00"),
        pytest.param(FRIDAY_NIGHT, datetime(2026, 10, 17, 2, tzinfo=CEST), False, id="fri-night-sat-02:00-end-excl"),
        # Same-day window, every day
        pytest.param(MORNING, datetime(2026, 10, 16, 5, 59, tzinfo=CEST), False, id="morning-05:59"),
        pytest.param(MORNING, datetime(2026, 10, 16, 6, tzinfo=CEST), True, id="morning-06:00-start-incl"),
        pytest.param(MORNING, datetime(2026, 10, 16, 8, 59, tzinfo=CEST), True, id="morning-08:59"),
        pytest.param(MORNING, datetime(2026, 10, 16, 9, tzinfo=CEST), False, id="morning-09:00-end-excl"),
        # Weekdays without a window use the local start date
        pytest.param(WEEKEND, datetime(2026, 10, 16, 23, 30, tzinfo=UTC), True, id="weekend-sat-01:30-local"),
        pytest.param(WEEKEND, datetime(2026, 10, 16, 21, tzinfo=UTC), False, id="weekend-fri-23:00-local"),
        # DST fall-back night 2026-10-25: 02:30 happens twice, both count for Saturday
        pytest.param(SATURDAY_LATE, datetime(2026, 10, 25, 0, 30, tzinfo=UTC), True, id="dst-2026-10-25-02:30-cest"),
        pytest.param(SATURDAY_LATE, datetime(2026, 10, 25, 1, 30, tzinfo=UTC), True, id="dst-2026-10-25-02:30-cet"),
        pytest.param(SATURDAY_LATE, datetime(2026, 10, 25, 3, 30, tzinfo=UTC), False, id="dst-2026-10-25-04:30-cet"),
        # DST spring-forward night 2027-03-28: 02:00-03:00 does not exist, 03:30 CEST still anchors to Saturday
        pytest.param(SATURDAY_LATE, datetime(2027, 3, 28, 1, 30, tzinfo=UTC), True, id="dst-2027-03-28-03:30-cest"),
        # D-12: incomplete or equal stored bounds and unknown weekday names never restrict or break the calendar
        pytest.param(
            {KEY_TIME_FROM: "22:00", KEY_TIME_TO: None}, datetime(2026, 10, 16, 12, tzinfo=CEST), True, id="from-only"
        ),
        pytest.param({KEY_TIME_TO: "02:00"}, datetime(2026, 10, 16, 12, tzinfo=CEST), True, id="to-only"),
        pytest.param(
            {KEY_TIME_FROM: "22:00", KEY_TIME_TO: "22:00"},
            datetime(2026, 10, 16, 12, tzinfo=CEST),
            True,
            id="from-eq-to",
        ),
        pytest.param({KEY_WEEKDAYS: ["xyz"]}, datetime(2026, 10, 14, 12, tzinfo=CEST), True, id="unknown-weekday"),
        pytest.param({KEY_WEEKDAYS: []}, datetime(2026, 10, 14, 12, tzinfo=CEST), True, id="empty-weekdays"),
    ],
)
def test_window_and_weekday_table(data: dict[str, Any], start: datetime, *, expected: bool) -> None:
    assert _passes(data, _timed(start)) is expected


START = datetime(2026, 10, 14, 20, tzinfo=CEST)


@pytest.mark.parametrize(
    ("data", "duration", "expected"),
    [
        # D-13: inclusive whole-minute bounds, exact timedelta comparison
        pytest.param({KEY_MIN_DURATION: 30, KEY_MAX_DURATION: 90}, timedelta(minutes=29), False, id="min30-max90-29"),
        pytest.param({KEY_MIN_DURATION: 30, KEY_MAX_DURATION: 90}, timedelta(minutes=30), True, id="min30-max90-30"),
        pytest.param({KEY_MIN_DURATION: 30, KEY_MAX_DURATION: 90}, timedelta(minutes=90), True, id="min30-max90-90"),
        pytest.param({KEY_MIN_DURATION: 30, KEY_MAX_DURATION: 90}, timedelta(minutes=91), False, id="min30-max90-91"),
        pytest.param({KEY_MIN_DURATION: 60}, timedelta(minutes=59, seconds=59), False, id="min60-59m59s"),
        pytest.param({KEY_MIN_DURATION: 60}, timedelta(minutes=60), True, id="min60-60"),
        pytest.param({KEY_MIN_DURATION: 60}, timedelta(days=2), True, id="min-only-no-upper-bound"),
        pytest.param({KEY_MAX_DURATION: 90}, timedelta(minutes=1), True, id="max-only-no-lower-bound"),
        pytest.param({KEY_MAX_DURATION: 90}, timedelta(minutes=90, seconds=1), False, id="max90-90m01s"),
        pytest.param({KEY_MIN_DURATION: None, KEY_MAX_DURATION: None}, timedelta(days=3), True, id="both-empty"),
        pytest.param({KEY_MIN_DURATION: 0}, timedelta(minutes=1), True, id="min-zero"),
    ],
)
def test_duration_bounds(data: dict[str, Any], duration: timedelta, *, expected: bool) -> None:
    assert _passes(data, _timed(START, START + duration)) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param({KEY_MIN_DURATION: 120}, True, id="dst-2026-10-25-120min-min120"),
        pytest.param({KEY_MAX_DURATION: 120}, True, id="dst-2026-10-25-120min-max120"),
        pytest.param({KEY_MAX_DURATION: 119}, False, id="dst-2026-10-25-120min-max119"),
        pytest.param({KEY_MIN_DURATION: 121}, False, id="dst-2026-10-25-120min-min121"),
    ],
)
def test_duration_across_dst_fall_back(data: dict[str, Any], *, expected: bool) -> None:
    # Pitfall 6: stop - start on the parser's fixed offsets is the real duration, not the 60 min wall-clock difference
    programme = _timed(datetime(2026, 10, 25, 1, 30, tzinfo=CEST), datetime(2026, 10, 25, 2, 30, tzinfo=CET))

    assert _passes(data, programme) is expected


def test_absurd_stop_hidden_by_max_duration() -> None:
    # WR-07: a stop three days after the start is hidden by a max duration
    programme = _timed(datetime(2026, 10, 13, 10, tzinfo=UTC), datetime(2026, 10, 16, 10, tzinfo=UTC))

    assert not _passes({KEY_MAX_DURATION: 600}, programme)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param({KEY_MIN_DURATION: 10**16}, False, id="huge-min-hides"),
        pytest.param({KEY_MAX_DURATION: 10**16}, True, id="huge-max-unbounded"),
    ],
)
def test_huge_stored_duration_does_not_raise(data: dict[str, Any], *, expected: bool) -> None:
    # with_defaults keeps any non-negative int; timedelta(minutes=10**16) would overflow
    assert _passes(data, _timed(START)) is expected


def test_every_constraint_must_pass() -> None:
    # D-14: channel AND include AND NOT exclude AND duration AND window AND weekday
    evening = datetime(2026, 10, 16, 20, 15, tzinfo=CEST)  # a Friday
    hit = _timed(evening, evening + timedelta(minutes=90), title="Tatort")
    others = (
        _timed(evening, evening + timedelta(minutes=90), channel="zdf.de", title="Tatort"),  # wrong channel
        _timed(evening, evening + timedelta(minutes=90), title="Tagesschau"),  # include misses
        _timed(evening, evening + timedelta(minutes=90), title="Tatort Wiederholung"),  # excluded
        _timed(evening, evening + timedelta(minutes=10), title="Tatort"),  # too short
        _timed(evening - timedelta(hours=3), evening - timedelta(hours=1, minutes=30), title="Tatort"),  # before window
        _timed(evening + timedelta(days=1), evening + timedelta(days=1, minutes=90), title="Tatort"),  # Saturday
    )
    data = {
        KEY_CHANNELS: ["ch.de"],
        KEY_INCLUDE: "tatort",
        KEY_EXCLUDE: "wiederholung",
        KEY_MIN_DURATION: 45,
        KEY_MAX_DURATION: 120,
        KEY_TIME_FROM: "20:00",
        KEY_TIME_TO: "23:00",
        KEY_WEEKDAYS: ["fri"],
    }

    result = FilterSpec.from_mapping(data).apply(_timed_epg(hit, *others), tz=BERLIN)

    assert result.matches == (hit,)


def test_filtering_keeps_feed_order_for_equal_starts() -> None:
    start = datetime(2026, 10, 16, 22, tzinfo=CEST)
    programmes = (
        _timed(start, channel="a.de", title="Zulu"),
        _timed(start, channel="b.de", title="Able"),
        _timed(start, channel="b.de", title="Bravo"),
        _timed(start + timedelta(hours=1), channel="a.de", title="Alpha"),
    )
    data = {**FRIDAY_NIGHT, KEY_MIN_DURATION: 30}

    assert FilterSpec.from_mapping(data).apply(_timed_epg(*programmes), tz=BERLIN).matches == programmes


def test_apply_without_tz_evaluates_in_utc() -> None:
    programme = _timed(datetime(2026, 10, 14, 7, tzinfo=UTC))  # 09:00 in Berlin
    spec = FilterSpec.from_mapping(MORNING)

    assert spec.apply(_timed_epg(programme)).matches == (programme,)
    assert spec.apply(_timed_epg(programme), tz=BERLIN).matches == ()


# --- Nested repetition guard (WR-01, T-02-08) ------------------------------------------------------------------------

NESTED = "nested repetition can be very slow"


@pytest.mark.parametrize(
    ("pattern", "rejected"),
    [
        pytest.param(r"^(\w+\s?)+$", True, id="word-groups"),
        pytest.param(r"(a*)*", True, id="star-in-star"),
        pytest.param(r"(\d+\s*)+x", True, id="digits-in-plus"),
        pytest.param(r"(formel|formula)\s*1", False, id="alternation"),
        pytest.param(r"^Tatort$", False, id="literal"),
        pytest.param(r"(?:a+)++", False, id="possessive"),
        pytest.param(r"(?>a+)+", False, id="atomic-group"),
        pytest.param(r"(ab){2,5}", False, id="bounded-group"),
        pytest.param(r"[a-z]+\d*", False, id="sequential-repeats"),
    ],
)
def test_nested_repetition_table(pattern: str, *, rejected: bool) -> None:
    expected = InvalidPattern(pattern=pattern, message=NESTED) if rejected else None

    assert first_invalid_pattern(pattern) == expected
    assert has_nested_repeat(pattern) is rejected


def test_first_invalid_pattern_rejects_nested_repetition() -> None:
    assert first_invalid_pattern("ok\n^(\\w+\\s?)+$") == InvalidPattern(pattern=r"^(\w+\s?)+$", message=NESTED)


def test_caps_checked_before_shape() -> None:
    line = "(a*)*" * 60 + "a"  # 301 characters

    result = first_invalid_pattern(line)

    assert result == InvalidPattern(pattern=line, message="pattern longer than 300 characters")


def test_shape_check_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(filter_module, "_sre_parse", None, raising=False)

    assert not has_nested_repeat("(a*)*")
    assert first_invalid_pattern("(a*)*") is None
    assert first_invalid_pattern("a" * 301) is not None  # the caps still apply


def test_residual_overlapping_alternation_documented() -> None:
    # Accepted residual risk (T-02-08): overlapping alternation under a repeat is not detected
    assert first_invalid_pattern("(a|aa)+") is None
    assert not has_nested_repeat("(a|aa)+")
