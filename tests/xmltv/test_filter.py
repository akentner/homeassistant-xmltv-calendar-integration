"""Filter engine truth table: channel AND (include empty OR any include) AND NOT any exclude (D-02 to D-08)."""

import unicodedata
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from custom_components.xmltv_calendar.xmltv.filter import FilterSpec, first_invalid_pattern
from custom_components.xmltv_calendar.xmltv.model import Channel, EpgData, ParseStats, Programme
from custom_components.xmltv_calendar.xmltv.settings import (
    FIELD_CATEGORY,
    FIELD_DESCRIPTION,
    FIELD_SUBTITLE,
    FIELD_TITLE,
    KEY_CASE_SENSITIVE,
    KEY_CHANNEL_REGEX,
    KEY_EXCLUDE,
    KEY_EXCLUDE_FIELDS,
    KEY_INCLUDE,
    KEY_INCLUDE_FIELDS,
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
