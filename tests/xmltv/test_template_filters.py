"""The custom template filters of D-06 and the D-07 recipes, rendered through the real EventTemplates facade."""

import logging
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from typing import Any

import pytest

from custom_components.xmltv_calendar.xmltv.model import Channel, Programme
from custom_components.xmltv_calendar.xmltv.render import EventTemplates, template_values, to_event_fields
from custom_components.xmltv_calendar.xmltv.settings import KEY_DESCRIPTION_TEMPLATE, KEY_TITLE_TEMPLATE
from custom_components.xmltv_calendar.xmltv.template_engine import (
    ENV,
    INVALID_TEMPLATE,
    UNKNOWN_FILTER,
    UNKNOWN_PLACEHOLDER,
    UNSUPPORTED_SYNTAX,
    TemplateError,
    compile_template,
    format_time,
    split,
)

CHANNEL = Channel(id="daserste.de", display_name="Das Erste")
START = datetime(2026, 10, 13, 18, tzinfo=UTC)


def _programme(title: str = "Formel 1: Großer Preis von Mexiko", description: str | None = None) -> Programme:
    return Programme(
        channel_id="daserste.de",
        start=START,
        stop=START + timedelta(minutes=90),
        titles=(title,),
        sub_titles=(),
        description=description,
        categories=(),
        episode=None,
    )


def _title(template: str, programme: Programme, *, tz: tzinfo | None = None) -> str:
    templates = EventTemplates.from_mapping({KEY_TITLE_TEMPLATE: template})
    return to_event_fields(programme, CHANNEL, templates, tz=tz)["summary"]


def _description(template: str, programme: Programme) -> str | None:
    templates = EventTemplates.from_mapping({KEY_DESCRIPTION_TEMPLATE: template})
    return to_event_fields(programme, CHANNEL, templates)["description"]


# --- D-07 recipes: first_line and lines ------------------------------------------------------------------------------


def test_first_description_line_as_title_part() -> None:
    programme = _programme("Formel 1", "Qualifying\nMehr Text")
    assert _title("{{ channel }}: {{ description | first_line }}", programme) == "Das Erste: Qualifying"


def test_missing_description_cleans_the_dangling_separator() -> None:
    assert _title("{{ channel }}: {{ description | first_line }}", _programme("Formel 1")) == "Das Erste"


def test_a_title_template_that_renders_nothing_falls_back_to_the_programme_title() -> None:
    assert _title("{{ description | first_line }}", _programme("Formel 1")) == "Formel 1"


def test_optional_sub_title_behind_if() -> None:
    template = "{% set sub = description | first_line %}{{ title }}{% if sub %} - {{ sub }}{% endif %}"
    assert _title(template, _programme("Formel 1")) == "Formel 1"
    assert _title(template, _programme("Formel 1", "Qualifying\nMehr Text")) == "Formel 1 - Qualifying"


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("\n  \n  Zweite Zeile  \nDritte", "Zweite Zeile"),
        ("Erste\nZweite", "Erste"),
        ("  Eine  ", "Eine"),
        ("", ""),
        (None, ""),
    ],
)
def test_first_line_skips_blank_lines_and_strips(description: str | None, expected: str) -> None:
    assert _title("[{{ description | first_line }}]", _programme("T", description)) == f"[{expected}]"


def test_lines_drops_blank_lines_and_strips_each() -> None:
    programme = _programme("T", "  Eins \n\n  Zwei\n   \nDrei  ")
    assert _title("{{ description | lines | length }}", programme) == "3"
    assert _title("{{ description | lines | join('|') }}", programme) == "Eins|Zwei|Drei"


@pytest.mark.parametrize("description", ["", None])
def test_lines_of_a_missing_description_is_an_empty_list(description: str | None) -> None:
    programme = _programme("Tagesschau", description)
    assert _title("{{ description | lines | length }}{{ title }}", programme) == "0Tagesschau"


def test_first_line_and_lines_treat_an_undefined_value_as_empty() -> None:
    programme = _programme("Tagesschau")
    template = "[{{ categories[3] | first_line }}|{{ categories[3] | lines | length }}]"
    assert _title(template, programme) == "[|0]"


# --- The engine-level helper: render straight through the compiled template, so errors are not swallowed --------------


def _render(template: str, programme: Programme | None = None, *, tz: tzinfo | None = None, **overrides: Any) -> str:
    values = template_values(programme or _programme(), CHANNEL, tz=tz) | overrides
    return compile_template(template).render(**values)


# --- split ---------------------------------------------------------------------------------------------------------


def test_split_takes_the_part_before_and_after_the_separator() -> None:
    assert _render("{{ title | split(':') | first }}") == "Formel 1"
    assert _render("{{ title | split(':') | last | trim }}") == "Großer Preis von Mexiko"


def test_split_maxsplit_whitespace_default_and_empty_separator() -> None:
    assert _render("{{ 'a:b:c' | split(':', 1) | join('|') }}") == "a|b:c"
    assert _render("{{ 'a:b:c' | split(':', maxsplit=1) | last }}") == "b:c"
    assert _render("{{ '  a   b  c ' | split | join('|') }}") == "a|b|c"
    assert _render("{{ 'a:b' | split('') | join('|') }}") == "a:b"
    assert _render("{{ 'a:b' | split('') | length }}") == "1"


def test_split_of_missing_text_is_an_empty_list() -> None:
    assert _render("{{ description | split(':') | length }}") == "0"
    assert _render("{{ categories[3] | split(':') | length }}") == "0"
    assert split(None, ":") == []
    assert split("", ":") == []


# --- regex_search ---------------------------------------------------------------------------------------------------


def test_regex_search_is_a_boolean_for_if() -> None:
    template = "{% if title | regex_search('^Formel') %}F1{% else %}other{% endif %}"
    assert _render(template) == "F1"
    assert _render(template, title="Tagesschau") == "other"
    assert _render("{{ title | regex_search('Mexiko') }}") == "True"
    assert _render("{{ title | regex_search('Spa') }}") == "False"


def test_regex_search_ignorecase_and_missing_text() -> None:
    assert _render("{{ title | regex_search('^FORMEL', ignorecase=true) }}") == "True"
    assert _render("{{ title | regex_search('^FORMEL', true) }}") == "True"
    assert _render("{{ title | regex_search('^FORMEL') }}") == "False"
    assert _render("{{ description | regex_search('x') }}") == "False"
    assert _render("{{ categories[3] | regex_search('x') }}") == "False"


@pytest.mark.parametrize(
    ("template", "reason"),
    [
        ("{{ title | regex_search('(') }}", INVALID_TEMPLATE),
        ("{{ title | regex_search('(a+)+$') }}", INVALID_TEMPLATE),
        ("{{ title | regex_search(subtitle) }}", UNSUPPORTED_SYNTAX),
    ],
)
def test_regex_search_arguments_are_validated_at_compile_time(template: str, reason: str) -> None:
    with pytest.raises(TemplateError) as err:
        compile_template(template)
    assert err.value.reason == reason


# --- strip_prefix, strip_suffix, remove -----------------------------------------------------------------------------


def test_strip_prefix_and_suffix_remove_the_exact_text_once() -> None:
    assert _render("{{ title | strip_prefix('Formel 1: ') }}") == "Großer Preis von Mexiko"
    assert _render("{{ 'xxabc' | strip_prefix('x') }}") == "xabc"
    assert _render("{{ 'abc (Wh.)' | strip_suffix(' (Wh.)') }}") == "abc"
    assert _render("{{ 'abcxx' | strip_suffix('x') }}") == "abcx"


def test_strip_prefix_and_suffix_leave_a_value_that_does_not_match_unchanged() -> None:
    assert _render("{{ title | strip_prefix('Spa') }}") == "Formel 1: Großer Preis von Mexiko"
    assert _render("{{ title | strip_suffix('Spa') }}") == "Formel 1: Großer Preis von Mexiko"
    title = _programme().title
    assert _render("{{ title | strip_prefix('') }}|{{ title | strip_suffix('') }}") == f"{title}|{title}"
    assert _render("{{ description | strip_prefix('x') }}[{{ categories[3] | strip_suffix('x') }}]") == "[]"


def test_remove_deletes_every_occurrence_of_each_part() -> None:
    assert _render("{{ 'a-b-c_d' | remove('-', '_') }}") == "abcd"
    assert _render("{{ 'a-b-c' | remove('-') }}") == "abc"
    assert _render("{{ 'a-b' | remove('', '-') }}") == "ab"
    assert _render("{{ 'a-b' | remove }}") == "a-b"
    assert _render("[{{ categories[3] | remove('x') }}]") == "[]"


# --- time -----------------------------------------------------------------------------------------------------------


ONE_HOUR = timezone(timedelta(hours=1))


def test_time_formats_start_and_end_in_the_zone_the_caller_converted_them_to() -> None:
    programme = _programme()
    assert _title("{{ start | time('%H:%M') }}", programme, tz=ONE_HOUR) == "19:00"
    assert _title("{{ start | time('%H:%M') }}", programme) == "18:00"  # no zone: as parsed (UTC here)
    assert _title("{{ end | time('%d.%m.') }}", programme, tz=ONE_HOUR) == "13.10."
    assert _title("{{ end | time }}", programme, tz=ONE_HOUR) == "20:30"  # default format %H:%M
    assert _title("{{ channel }} {{ start | time('%H:%M') }}", programme, tz=ONE_HOUR) == "Das Erste 19:00"


def test_time_of_a_value_that_is_not_a_datetime_renders_empty() -> None:
    assert _render("[{{ title | time('%H:%M') }}]") == "[]"
    assert _render("[{{ categories[3] | time }}]") == "[]"
    assert format_time(None) == ""
    assert _render("[{{ 5 | time }}]") == "[]"


def test_time_with_a_non_text_format_uses_the_default() -> None:
    assert _render("{{ start | time(5) }}", tz=ONE_HOUR) == "19:00"
    assert _render("{{ start | time(none) }}", tz=ONE_HOUR) == "19:00"


def test_a_malformed_directive_is_a_render_error_not_a_compile_error() -> None:
    class Broken(datetime):
        def strftime(self, format: str) -> str:  # noqa: A002 - mirrors the datetime signature
            msg = "bad directive"
            raise ValueError(msg)

    broken = Broken(2026, 10, 13, 18, tzinfo=UTC)
    template = compile_template("{{ start | time('%Q') }}")  # compiles
    with pytest.raises(ValueError, match="bad directive"):
        template.render(start=broken)


# --- The D-06 vocabulary --------------------------------------------------------------------------------------------

D06_FILTERS = (
    "split",
    "join",
    "replace",
    "trim",
    "truncate",
    "first",
    "last",
    "select",
    "reject",
    "map",
    "default",
    "upper",
    "title",
    "length",
    "regex_replace",
    "regex_search",
    "strip_prefix",
    "strip_suffix",
    "remove",
    "lines",
    "first_line",
    "time",
)
SMOKE = {
    "split": "{{ title | split(':') | length }}",
    "join": "{{ titles | join('/') }}",
    "replace": "{{ title | replace('a', 'b') }}",
    "trim": "{{ title | trim }}",
    "truncate": "{{ title | truncate(5) }}",
    "first": "{{ titles | first }}",
    "last": "{{ titles | last }}",
    "select": "{{ titles | select('string') | list | length }}",
    "reject": "{{ titles | reject('none') | list | length }}",
    "map": "{{ titles | map('upper') | join }}",
    "default": "{{ categories[3] | default('x') }}",
    "upper": "{{ title | upper }}",
    "title": "{{ title | title }}",
    "length": "{{ title | length }}",
    "regex_replace": "{{ title | regex_replace('a', 'b') }}",
    "regex_search": "{{ title | regex_search('a') }}",
    "strip_prefix": "{{ title | strip_prefix('F') }}",
    "strip_suffix": "{{ title | strip_suffix('o') }}",
    "remove": "{{ title | remove('a') }}",
    "lines": "{{ description | lines | length }}",
    "first_line": "{{ description | first_line }}",
    "time": "{{ start | time }}",
}


def test_every_d06_filter_is_available() -> None:
    assert set(SMOKE) == set(D06_FILTERS)
    missing = [name for name in D06_FILTERS if name not in ENV.filters]
    assert not missing
    for name in D06_FILTERS:
        _render(SMOKE[name], _programme("Formel 1: Mexiko", "Eins\nZwei"))


def test_the_tilde_operator_joins_text() -> None:
    assert _render("{{ channel ~ ': ' ~ title }}") == "Das Erste: Formel 1: Großer Preis von Mexiko"


@pytest.mark.parametrize("name", ["now", "states", "hass", "environ", "config"])
def test_no_filter_global_or_variable_reads_ha_state_the_clock_or_the_environment(name: str) -> None:
    with pytest.raises(TemplateError) as err:
        compile_template("{{ " + name + " }}")
    assert err.value.reason == UNKNOWN_PLACEHOLDER
    assert err.value.detail == name
    with pytest.raises(TemplateError) as err:
        compile_template("{{ " + name + "('x') }}")
    assert err.value.reason in {UNKNOWN_PLACEHOLDER, UNSUPPORTED_SYNTAX}
    with pytest.raises(TemplateError) as err:
        compile_template("{{ title | " + name + " }}")
    assert err.value.reason == UNKNOWN_FILTER


def test_custom_filters_never_expose_the_environment() -> None:
    assert not {"now", "states", "env", "environ", "getenv", "is_state", "state_attr", "utcnow"} & set(ENV.filters)


# --- An oversized replace falls back to the programme title (D-03, T-05-11) -------------------------------------------


def test_an_oversized_replace_falls_back_with_one_warning_and_no_feed_text(caplog: pytest.LogCaptureFixture) -> None:
    feed_title = "a" * 5000  # 5000 characters times a 300 character replacement is far over the 50000 limit
    template = "{{ title | replace('a', '" + "b" * 300 + "') }}"
    templates = EventTemplates.from_mapping({KEY_TITLE_TEMPLATE: template}, "F1 calendar")
    programme = _programme(feed_title)
    with caplog.at_level(logging.DEBUG, logger="custom_components.xmltv_calendar.xmltv.render"):
        first = to_event_fields(programme, CHANNEL, templates)["summary"]
        second = to_event_fields(programme, CHANNEL, templates)["summary"]
    assert first == second == feed_title
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "F1 calendar" in warnings[0].getMessage()
    assert "ValueError" in warnings[0].getMessage()
    assert "aaaa" not in caplog.text
    assert "bbbb" not in caplog.text
