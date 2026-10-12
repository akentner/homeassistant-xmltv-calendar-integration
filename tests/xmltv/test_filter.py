"""Filter engine truth table: channel AND (include empty OR any include) AND NOT any exclude (D-02 to D-08)."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from custom_components.xmltv_calendar.xmltv.filter import FilterSpec, first_invalid_pattern
from custom_components.xmltv_calendar.xmltv.model import Channel, EpgData, ParseStats, Programme

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
