"""Stored calendar settings contract: defaults, tolerant reads, idempotency and has_advanced (D-03, D-06)."""

from typing import Any

import pytest

from custom_components.xmltv_calendar.xmltv.settings import (
    ADVANCED_DEFAULTS,
    DEFAULT_TITLE_TEMPLATE,
    FIELD_CATEGORY,
    FIELD_DESCRIPTION,
    FIELD_SUBTITLE,
    FIELD_TITLE,
    KEY_CASE_SENSITIVE,
    KEY_CHANNEL_REGEX,
    KEY_CHANNELS,
    KEY_DESCRIPTION_TEMPLATE,
    KEY_EXCLUDE,
    KEY_EXCLUDE_FIELDS,
    KEY_INCLUDE,
    KEY_INCLUDE_FIELDS,
    KEY_MAX_DURATION,
    KEY_MIN_DURATION,
    KEY_TIME_FROM,
    KEY_TIME_TO,
    KEY_TITLE_TEMPLATE,
    KEY_WEEKDAYS,
    has_advanced,
    normalize_time,
    with_defaults,
)

FULL_DEFAULTS: dict[str, Any] = {
    KEY_CHANNELS: [],
    KEY_CHANNEL_REGEX: "",
    KEY_INCLUDE: "",
    KEY_EXCLUDE: "",
    KEY_INCLUDE_FIELDS: [FIELD_TITLE, FIELD_SUBTITLE],
    KEY_EXCLUDE_FIELDS: [FIELD_TITLE, FIELD_SUBTITLE],
    KEY_CASE_SENSITIVE: False,
    KEY_TIME_FROM: None,
    KEY_TIME_TO: None,
    KEY_WEEKDAYS: [],
    KEY_MIN_DURATION: None,
    KEY_MAX_DURATION: None,
    KEY_TITLE_TEMPLATE: DEFAULT_TITLE_TEMPLATE,
    KEY_DESCRIPTION_TEMPLATE: "",
    "retention_days": 1,
}
PHASE1_DATA: dict[str, Any] = {
    KEY_CHANNELS: ["daserste.de"],
    KEY_CHANNEL_REGEX: "^sky",
    KEY_INCLUDE: "formel",
    KEY_EXCLUDE: "",
}


def test_key_names_are_the_flat_contract() -> None:
    # 02-02 Task 2 decision "flat": these exact strings are persisted in every calendar subentry
    assert list(FULL_DEFAULTS) == [
        "channels",
        "channel_regex",
        "include",
        "exclude",
        "include_fields",
        "exclude_fields",
        "case_sensitive",
        "time_from",
        "time_to",
        "weekdays",
        "min_duration",
        "max_duration",
        "title_template",
        "description_template",
        "retention_days",
    ]
    assert (FIELD_TITLE, FIELD_SUBTITLE, FIELD_DESCRIPTION, FIELD_CATEGORY) == (
        "title",
        "subtitle",
        "description",
        "category",
    )


def test_with_defaults_of_empty_mapping() -> None:
    assert with_defaults({}) == FULL_DEFAULTS


def test_with_defaults_keeps_given_values() -> None:
    assert with_defaults({KEY_INCLUDE: "x"}) == {**FULL_DEFAULTS, KEY_INCLUDE: "x"}


def test_with_defaults_keeps_phase1_data() -> None:
    assert with_defaults(PHASE1_DATA) == {**FULL_DEFAULTS, **PHASE1_DATA}


def test_advanced_defaults_are_the_phase2_defaults() -> None:
    assert dict(ADVANCED_DEFAULTS) == {key: FULL_DEFAULTS[key] for key in list(FULL_DEFAULTS)[4:]}


@pytest.mark.parametrize(
    ("key", "stored", "expected"),
    [
        pytest.param(KEY_INCLUDE_FIELDS, "title", [FIELD_TITLE, FIELD_SUBTITLE], id="fields-string"),
        pytest.param(KEY_INCLUDE_FIELDS, [FIELD_TITLE, "bogus", FIELD_TITLE], [FIELD_TITLE], id="fields-unknown-dup"),
        pytest.param(KEY_INCLUDE_FIELDS, [], [FIELD_TITLE, FIELD_SUBTITLE], id="fields-empty"),
        pytest.param(KEY_INCLUDE_FIELDS, None, [FIELD_TITLE, FIELD_SUBTITLE], id="fields-none"),
        pytest.param(KEY_INCLUDE_FIELDS, ["bogus"], [FIELD_TITLE, FIELD_SUBTITLE], id="fields-only-unknown"),
        pytest.param(
            KEY_EXCLUDE_FIELDS,
            [FIELD_CATEGORY, FIELD_DESCRIPTION, FIELD_TITLE],
            [FIELD_TITLE, FIELD_DESCRIPTION, FIELD_CATEGORY],
            id="fields-ordered",
        ),
        pytest.param(KEY_EXCLUDE_FIELDS, [FIELD_CATEGORY, 5, {}], [FIELD_CATEGORY], id="fields-wrong-items"),
        pytest.param(KEY_CASE_SENSITIVE, "yes", False, id="case-string"),
        pytest.param(KEY_CASE_SENSITIVE, 1, False, id="case-int"),
        pytest.param(KEY_CASE_SENSITIVE, True, True, id="case-true"),
        pytest.param(KEY_TIME_FROM, "22:00:00", "22:00", id="time-with-seconds"),
        pytest.param(KEY_TIME_FROM, "22:00", "22:00", id="time-hh-mm"),
        pytest.param(KEY_TIME_TO, "25:00", None, id="time-out-of-range"),
        pytest.param(KEY_TIME_TO, 2200, None, id="time-int"),
        pytest.param(KEY_TIME_TO, "22", None, id="time-hours-only"),
        pytest.param(KEY_TIME_TO, "22:00+01:00", None, id="time-with-offset"),
        pytest.param(KEY_WEEKDAYS, ["fri", "xyz", "fri", "mon"], ["mon", "fri"], id="weekdays-ordered"),
        pytest.param(KEY_WEEKDAYS, "fri", [], id="weekdays-string"),
        pytest.param(KEY_MIN_DURATION, 90.0, 90, id="duration-float"),
        pytest.param(KEY_MIN_DURATION, 0, 0, id="duration-zero"),
        pytest.param(KEY_MIN_DURATION, -5, None, id="duration-negative"),
        pytest.param(KEY_MIN_DURATION, True, None, id="duration-bool"),
        pytest.param(KEY_MAX_DURATION, "90", None, id="duration-string"),
        pytest.param(KEY_MAX_DURATION, float("nan"), None, id="duration-nan"),
        pytest.param(KEY_MAX_DURATION, float("inf"), None, id="duration-inf"),
        pytest.param(KEY_TITLE_TEMPLATE, "", DEFAULT_TITLE_TEMPLATE, id="title-template-empty"),
        pytest.param(KEY_TITLE_TEMPLATE, "   ", DEFAULT_TITLE_TEMPLATE, id="title-template-blank"),
        pytest.param(KEY_TITLE_TEMPLATE, 5, DEFAULT_TITLE_TEMPLATE, id="title-template-int"),
        pytest.param(KEY_TITLE_TEMPLATE, "{title}", "{title}", id="title-template-kept"),
        pytest.param(KEY_DESCRIPTION_TEMPLATE, None, "", id="description-template-none"),
        pytest.param(KEY_DESCRIPTION_TEMPLATE, "{description}", "{description}", id="description-template-kept"),
        pytest.param(KEY_CHANNELS, "zdf.de", ["zdf.de"], id="channels-string"),
        pytest.param(KEY_CHANNELS, ["zdf.de", "", "zdf.de", "sky.de"], ["zdf.de", "sky.de"], id="channels-dedup"),
        pytest.param(KEY_CHANNELS, 5, [], id="channels-int"),
        pytest.param(KEY_INCLUDE, None, "", id="include-none"),
        pytest.param(KEY_EXCLUDE, ["x"], "", id="exclude-list"),
    ],
)
def test_with_defaults_tolerant_read(key: str, stored: object, expected: object) -> None:
    assert with_defaults({key: stored}) == {**FULL_DEFAULTS, key: expected}


GARBAGE: dict[str, Any] = {
    KEY_CHANNELS: {"a": 1},
    KEY_CHANNEL_REGEX: 3,
    KEY_INCLUDE: b"x",
    KEY_EXCLUDE: None,
    KEY_INCLUDE_FIELDS: [[], None],
    KEY_EXCLUDE_FIELDS: object(),
    KEY_CASE_SENSITIVE: None,
    KEY_TIME_FROM: "",
    KEY_TIME_TO: [],
    KEY_WEEKDAYS: [None, 0],
    KEY_MIN_DURATION: [],
    KEY_MAX_DURATION: "x",
    KEY_TITLE_TEMPLATE: None,
    KEY_DESCRIPTION_TEMPLATE: 1.5,
    "unknown": "dropped",
}


def test_with_defaults_never_raises_and_drops_unknown_keys() -> None:
    assert with_defaults(GARBAGE) == FULL_DEFAULTS


@pytest.mark.parametrize(
    "data",
    [
        {},
        PHASE1_DATA,
        GARBAGE,
        {KEY_INCLUDE_FIELDS: [FIELD_CATEGORY, FIELD_TITLE], KEY_TIME_FROM: "22:00:00", KEY_MIN_DURATION: 45.0},
        {KEY_WEEKDAYS: ["sun", "sat"], KEY_TITLE_TEMPLATE: "{title}", KEY_CASE_SENSITIVE: True},
    ],
)
def test_with_defaults_is_idempotent(data: dict[str, Any]) -> None:
    once = with_defaults(data)
    assert with_defaults(once) == once


def test_with_defaults_returns_fresh_lists() -> None:
    first = with_defaults({})
    first[KEY_INCLUDE_FIELDS].append(FIELD_CATEGORY)
    first[KEY_WEEKDAYS].append("mon")

    assert with_defaults({}) == FULL_DEFAULTS
    assert dict(ADVANCED_DEFAULTS) == {key: FULL_DEFAULTS[key] for key in list(FULL_DEFAULTS)[4:]}


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param({}, False, id="empty"),
        pytest.param(PHASE1_DATA, False, id="phase1"),
        pytest.param(FULL_DEFAULTS, False, id="explicit-defaults"),
        pytest.param({KEY_INCLUDE_FIELDS: [FIELD_SUBTITLE, FIELD_TITLE]}, False, id="default-fields-reordered"),
        pytest.param({KEY_TIME_FROM: "", KEY_MIN_DURATION: -1}, False, id="invalid-values-are-defaults"),
        pytest.param({KEY_WEEKDAYS: ["sat"]}, True, id="weekdays"),
        pytest.param({KEY_TITLE_TEMPLATE: "{title}"}, True, id="title-template"),
        pytest.param({KEY_CASE_SENSITIVE: True}, True, id="case-sensitive"),
        pytest.param({KEY_EXCLUDE_FIELDS: [FIELD_DESCRIPTION]}, True, id="exclude-fields"),
        pytest.param({KEY_MAX_DURATION: 0}, True, id="zero-duration"),
    ],
)
def test_has_advanced(data: dict[str, Any], *, expected: bool) -> None:
    assert has_advanced(data) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("00:00", "00:00"),
        ("23:59:59", "23:59"),
        ("07:05", "07:05"),
        ("7:05", None),
        ("24:00", None),
        ("12:60", None),
        ("", None),
        (None, None),
        (1200, None),
        ("ab:cd", None),
    ],
)
def test_normalize_time(value: object, expected: str | None) -> None:
    assert normalize_time(value) == expected
