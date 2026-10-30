"""The sandboxed Jinja engine: whitelist, error reasons, regex validation and sandbox (D-01, D-03, D-04, D-08)."""

import contextlib
import time
from datetime import UTC, datetime
from typing import Any

import jinja2
import pytest
from jinja2.sandbox import SandboxedEnvironment

from custom_components.xmltv_calendar.xmltv import template_engine
from custom_components.xmltv_calendar.xmltv.filter import NESTED_REPETITION_MESSAGE
from custom_components.xmltv_calendar.xmltv.template_engine import (
    CUSTOM_FILTERS,
    ENV,
    INVALID_TEMPLATE,
    LEGACY_PLACEHOLDER,
    MAX_DESCRIPTION_TEMPLATE_LENGTH,
    MAX_FILTER_CHAIN,
    MAX_LITERAL_LENGTH,
    MAX_RESULT_CHARS,
    MAX_TITLE_TEMPLATE_LENGTH,
    TEMPLATE_ERROR_REASONS,
    TEMPLATE_RUNTIME_ERROR,
    UNKNOWN_FILTER,
    UNKNOWN_PLACEHOLDER,
    UNSUPPORTED_SYNTAX,
    VARIABLE_ORDER,
    VARIABLES,
    TemplateError,
    compile_template,
    regex_replace,
)

START = datetime(2026, 10, 13, 18, tzinfo=UTC)
# The variables a programme produces, as render.template_values builds them
VALUES: dict[str, Any] = {
    "channel": "Das Erste",
    "channel_id": "daserste.de",
    "title": "Formel 1: Großer Preis von Mexiko",
    "titles": ["Formel 1: Großer Preis von Mexiko", "Formula 1"],
    "subtitle": "Qualifying",
    "subtitles": ["Qualifying", "Teil 2"],
    "episode": "S01E04",
    "category": "Sport, Motorsport",
    "categories": ["Sport", "Motorsport", "Live"],
    "description": "Kommissarin ermittelt.\nZweite Zeile.",
    "start": START,
    "end": START,
}


def _render(text: str, **overrides: Any) -> str:
    return compile_template(text).render(**{**VALUES, **overrides})


def _reject(text: str, **kwargs: Any) -> TemplateError:
    started = time.perf_counter()
    with pytest.raises(TemplateError) as err:
        compile_template(text, **kwargs)
    assert time.perf_counter() - started < 1  # rejected by the walk, nothing evaluated (T-05-02)
    return err.value


# --- Rendering ------------------------------------------------------------------------------------------------------


def test_formula_one_prefix_recipe() -> None:
    assert _render("{{ title | regex_replace('^Formel ?1:? ?', '') }}") == "Großer Preis von Mexiko"
    assert _render("{{ title | regex_replace('^Formel ?1:? ?', '') }}", title="Tagesschau") == "Tagesschau"


@pytest.mark.parametrize(
    ("template", "overrides", "expected"),
    [
        ("{{ channel }}: {{ title }}", {}, "Das Erste: Formel 1: Großer Preis von Mexiko"),
        ("{% if subtitle %}{{ subtitle }}{% elif episode %}{{ episode }}{% else %}-{% endif %}", {}, "Qualifying"),
        (
            "{% if subtitle %}{{ subtitle }}{% elif episode %}{{ episode }}{% else %}-{% endif %}",
            {"subtitle": ""},
            "S01E04",
        ),
        (
            "{% if subtitle %}{{ subtitle }}{% elif episode %}{{ episode }}{% else %}-{% endif %}",
            {"subtitle": "", "episode": ""},
            "-",
        ),
        ("{% set sub = description %}{% if sub %}{{ sub }}{% endif %}", {"description": "Text"}, "Text"),
        ("{% set sub = description %}{% if sub %}{{ sub }}{% endif %}", {"description": ""}, ""),
        ("{% set a, b = categories[0], categories[1] %}{{ b }}/{{ a }}", {}, "Motorsport/Sport"),
        ("{{ categories[:2] | join('/') }}", {}, "Sport/Motorsport"),
        ("{{ categories[-1] }}", {}, "Live"),
        ("{{ categories[1:] | join('/') }}", {}, "Motorsport/Live"),
        ("{{ title ~ ' (' ~ channel ~ ')' }}", {"title": "A"}, "A (Das Erste)"),
        ("{{ 'yes' if 1 < 2 < 3 else 'no' }}", {}, "yes"),
        ("{{ 'yes' if 3 > 2 > 2 else 'no' }}", {}, "no"),
        ("{{ 'yes' if categories[5] is defined else 'no' }}", {}, "no"),
        ("{{ 'yes' if categories[0] is defined else 'no' }}", {}, "yes"),
        ("{{ 'yes' if subtitle is string and subtitle is not none else 'no' }}", {}, "yes"),
        ("{{ description | truncate(10, killwords=true) }}", {}, "Kommiss..."),
        ("{{ title | regex_replace('^FORMEL ?1:? ?', '', ignorecase=true) }}", {}, "Großer Preis von Mexiko"),
        ("{{ title | regex_replace('^FORMEL ?1:? ?', '', true) }}", {}, "Großer Preis von Mexiko"),
        ("{{ title | regex_replace('^FORMEL ?1:? ?', '') }}", {}, "Formel 1: Großer Preis von Mexiko"),
        ("{{ 7 // 2 }} {{ 7 / 2 }} {{ 7 - 2 }} {{ -3 | abs }}", {}, "3 3.5 5 3"),
        (
            "{{ titles | length }}|{{ titles | first }}|{{ titles | last }}",
            {},
            "2|Formel 1: Großer Preis von Mexiko|Formula 1",
        ),
        ("{{ category | upper }}", {}, "SPORT, MOTORSPORT"),
    ],
)
def test_compile_and_render_table(template: str, overrides: dict[str, Any], expected: str) -> None:
    assert _render(template, **overrides) == expected


@pytest.mark.parametrize(
    "template",
    [
        "{{ categories[5] }}",
        "{{ categories[5] | upper }}",
        "{{ title.nope }}",
        "{{ title.nope.deeper | upper }}",
        "{{ subtitles[9] | regex_replace('a', 'b') }}",
        "{{ categories[5] | first }}",
    ],
)
def test_undefined_values_render_empty(template: str) -> None:
    # D-03: lenient undefined, so a missing field never fails a window
    assert _render(template) == ""


def test_empty_and_missing_fields_render_as_empty_strings() -> None:
    sparse = {"subtitle": "", "subtitles": [], "episode": "", "category": "", "categories": [], "description": ""}
    assert (
        _render("[{{ subtitle }}|{{ episode }}|{{ category }}|{{ description }}|{{ categories[0] }}]", **sparse)
        == "[||||]"
    )


def test_trim_blocks_leaves_no_blank_line_for_block_tags_on_their_own_lines() -> None:
    template = (
        "{% if subtitle %}\nSub: {{ subtitle }}\n{% endif %}\n{% if episode %}\nEp: {{ episode }}\n{% endif %}\nEnd"
    )
    assert _render(template) == "Sub: Qualifying\nEp: S01E04\nEnd"
    assert _render(template, subtitle="", episode="") == "End"


def test_whitespace_control_is_available() -> None:
    assert _render("{{ title -}}   {{ '!' }}", title="A") == "A!"


# --- Rejections: the whitelist (D-04, A6, A7) -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("template", "node"),
    [
        ("{% for c in categories %}{{ c }}{% endfor %}", "For"),
        ("{% macro m() %}x{% endmacro %}{{ m() }}", "Macro"),
        ("{% call title() %}x{% endcall %}", "CallBlock"),
        ("{% include 'x' %}", "Include"),
        ("{% import 'x' as y %}", "Import"),
        ("{% from 'x' import y %}", "FromImport"),
        ("{% extends 'x' %}", "Extends"),
        ("{% block b %}x{% endblock %}", "Block"),
        ("{% with a = 1 %}{{ a }}{% endwith %}", "With"),
        ("{% set x %}abc{% endset %}{{ x }}", "AssignBlock"),
        ("{% filter upper %}x{% endfilter %}", "FilterBlock"),
        ("{{ title.upper() }}", "Call"),
        ("{{ (title | upper).lower() }}", "Call"),
        ("{{ title * 3 }}", "Mul"),
        ("{{ 2 ** 3 }}", "Pow"),
        ("{{ 5 % 2 }}", "Mod"),
        ("{{ title + 'x' }}", "Add"),
        ("{{ {'a': 1} }}", "Dict"),
    ],
)
def test_unsupported_syntax_is_rejected(template: str, node: str) -> None:
    err = _reject(template)
    assert err.reason == UNSUPPORTED_SYNTAX
    assert err.detail.startswith(node)
    assert "line 1" in err.detail


def test_the_name_self_is_rejected() -> None:
    err = _reject("{{ self }}")
    assert err.reason == UNSUPPORTED_SYNTAX
    assert "self" in err.detail


def test_star_arguments_to_a_filter_are_rejected() -> None:
    assert _reject("{{ categories | join(*categories) }}").reason == UNSUPPORTED_SYNTAX
    assert _reject("{{ title | truncate(**subtitles) }}").reason == UNSUPPORTED_SYNTAX


def test_a_huge_constant_power_expression_is_rejected_before_it_is_evaluated() -> None:
    err = _reject("{{ (99 ** 99999999) | string | length }}")
    assert err.reason == UNSUPPORTED_SYNTAX
    assert err.detail.startswith("Pow")


@pytest.mark.parametrize("name", ["center", "format", "attr", "safe", "tojson", "indent", "e", "wordwrap", "urlize"])
def test_pruned_filters_are_unknown(name: str) -> None:
    err = _reject(f"{{{{ title | {name} }}}}")
    assert err.reason == UNKNOWN_FILTER
    assert err.detail == name


def test_unknown_filter_and_unknown_test_name_the_offender() -> None:
    err = _reject("{{ title | nope }}")
    assert (err.reason, err.detail) == (UNKNOWN_FILTER, "nope")
    err = _reject("{% if title is nope %}x{% endif %}")
    assert err.reason == UNKNOWN_FILTER
    assert err.detail == "nope"
    assert _reject("{% if title is divisibleby(3) %}x{% endif %}").reason == UNKNOWN_FILTER


def test_unknown_variables_are_listed_sorted() -> None:
    err = _reject("{{ nope }}")
    assert (err.reason, err.detail) == (UNKNOWN_PLACEHOLDER, "nope")
    err = _reject("{{ zeta }}{{ alpha }}{{ title }}")
    assert (err.reason, err.detail) == (UNKNOWN_PLACEHOLDER, "alpha, zeta")
    assert _reject("{{ titel }}").reason == UNKNOWN_PLACEHOLDER


@pytest.mark.parametrize("name", ["range", "dict", "lipsum", "cycler", "joiner", "namespace"])
def test_pruned_globals_are_unknown_variables(name: str) -> None:
    err = _reject(f"{{{{ {name} }}}}")
    assert err.reason == UNKNOWN_PLACEHOLDER
    assert err.detail == name


def test_a_name_assigned_by_set_is_not_flagged() -> None:
    assert _render("{% set sub = subtitle %}{{ sub }}") == "Qualifying"


def test_every_variable_is_known() -> None:
    for name in VARIABLE_ORDER:
        compile_template("{{ " + name + " }}")


def test_syntax_errors_name_the_line() -> None:
    err = _reject("{{ title")
    assert err.reason == INVALID_TEMPLATE
    assert err.detail.startswith("line 1")
    err = _reject("first line\n{% if title %}\nno end")
    assert err.reason == INVALID_TEMPLATE
    assert err.detail.startswith("line ")


def test_deeply_nested_input_is_a_template_error_not_a_crash() -> None:
    err = _reject("{{ " + "(" * 900 + "title" + ")" * 900 + " }}", max_length=5000)
    assert err.reason in {INVALID_TEMPLATE, UNSUPPORTED_SYNTAX}


@pytest.mark.parametrize(
    ("template", "detail"),
    [
        ("{channel}: {title}", "{channel}"),
        ("x {title}", "{title}"),
        ("{channel_id}", "{channel_id}"),
        ("{episode}", "{episode}"),
        ("{title} {{ channel }}", "{title}"),
        ("{% if title %}{title}{% endif %}", "{title}"),
        ("{{ title }}{channel_id}", "{channel_id}"),
        ("{%- if title -%}{description}{%- endif -%}", "{description}"),
    ],
)
def test_legacy_single_brace_text_is_detected(template: str, detail: str) -> None:
    err = _reject(template)
    assert err.reason == LEGACY_PLACEHOLDER
    assert err.detail == detail


def test_mixed_template_with_a_retired_name_is_rejected() -> None:
    """A partly migrated template no longer renders the literal {channel} into every title (WR-03)."""
    err = _reject("{channel} - {{ title }}")
    assert err.reason == LEGACY_PLACEHOLDER
    assert err.detail == "{channel}"


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("{{ title }} {live}", "T {live}"),
        ("{live}", "{live}"),
    ],
)
def test_names_outside_the_closed_set_stay_literal_text(template: str, expected: str) -> None:
    assert _render(template, title="T") == expected


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("{{ title }}", "T"),
        ("{% if title %}x{% endif %}", "x"),
        ("{# {title} #}{{ title }}", "T"),
        ("{{ '{title}' }}", "{title}"),
        ('{{ "a{title}b" | replace("{title}", "-") }}', "a-b"),
    ],
)
def test_braces_outside_literal_text_are_not_legacy(template: str, expected: str) -> None:
    assert _render(template, title="T") == expected


@pytest.mark.parametrize(
    ("template", "reason"),
    [
        ("{{ {'a': title} }}", UNSUPPORTED_SYNTAX),
        ("{{ {title} }}", INVALID_TEMPLATE),
    ],
)
def test_braces_inside_expressions_never_give_the_legacy_reason(template: str, reason: str) -> None:
    assert _reject(template).reason == reason


def test_text_longer_than_the_cap_is_rejected() -> None:
    err = _reject("a" * 11, max_length=10)
    assert err.reason == INVALID_TEMPLATE
    assert "longer than 10 characters" in err.detail
    compile_template("a" * 10, max_length=10)
    assert _reject("a" * (MAX_TITLE_TEMPLATE_LENGTH + 1)).reason == INVALID_TEMPLATE
    compile_template("a" * MAX_DESCRIPTION_TEMPLATE_LENGTH, max_length=MAX_DESCRIPTION_TEMPLATE_LENGTH)


# --- Regex arguments are validated at compile time (T-05-03) --------------------------------------------------------


def test_regex_pattern_must_be_a_text_literal() -> None:
    for template in (
        "{{ title | regex_replace(subtitle, '') }}",
        "{{ title | regex_replace(1, '') }}",
        "{{ title | regex_replace(('a' ~ 'b'), '') }}",
        "{{ title | regex_replace() }}",
    ):
        err = _reject(template)
        assert err.reason == UNSUPPORTED_SYNTAX, template
        assert "text literal" in err.detail


def test_invalid_regex_is_rejected() -> None:
    err = _reject("{{ title | regex_replace('(', '') }}")
    assert err.reason == INVALID_TEMPLATE
    assert err.detail


def test_nested_unbounded_repetition_is_rejected() -> None:
    err = _reject("{{ title | regex_replace('(a+)+$', '') }}")
    assert err.reason == INVALID_TEMPLATE
    assert err.detail == NESTED_REPETITION_MESSAGE


def test_overlong_pattern_is_rejected() -> None:
    err = _reject("{{ title | regex_replace('" + "a" * 301 + "', '') }}")
    assert err.reason == INVALID_TEMPLATE
    assert "300" in err.detail
    compile_template("{{ title | regex_replace('" + "a" * 300 + "', '') }}")


def test_replacement_with_a_bad_group_reference_is_rejected_at_compile_time() -> None:
    err = _reject(r"{{ title | regex_replace('a', '\\g<9>') }}")
    assert err.reason == INVALID_TEMPLATE
    assert _render(r"{{ title | regex_replace('(F)', '<\\1>') }}", title="Fx") == "<F>x"


def test_regex_replace_accepts_keyword_arguments() -> None:
    assert _render("{{ title | regex_replace(find='x', replace='y') }}", title="axb") == "ayb"


def test_regex_replace_function_treats_missing_values_as_empty() -> None:
    assert regex_replace(None, "a", "b") == ""
    assert regex_replace(jinja2.Undefined(), "a", "b") == ""
    assert regex_replace("abc", "B", "x", ignorecase=True) == "axc"
    assert regex_replace(12, "1", "x") == "x2"
    assert regex_replace("abc", "b") == "ac"


# --- Resource bounds (T-05-10, T-05-11) -----------------------------------------------------------------------------


def _chain(count: int) -> str:
    return "{{ title" + " | trim" * count + " }}"


def test_the_bounds_are_the_documented_constants() -> None:
    bounds = (MAX_FILTER_CHAIN, MAX_LITERAL_LENGTH, MAX_RESULT_CHARS)
    assert bounds == (16, 300, 50000)


def test_a_chain_of_16_filters_compiles_and_17_is_rejected() -> None:
    assert _render(_chain(16), title=" x ") == "x"
    err = _reject(_chain(17))
    assert err.reason == UNSUPPORTED_SYNTAX
    assert "16" in err.detail


@pytest.mark.parametrize("count", [143, 286])
def test_very_long_filter_chains_are_rejected_quickly(count: int) -> None:
    assert _reject(_chain(count), max_length=5000).reason == UNSUPPORTED_SYNTAX


def test_two_short_chains_in_one_template_are_not_summed() -> None:
    template = "{{ title" + " | trim" * 10 + " }}{{ subtitle" + " | trim" * 10 + " }}"
    assert _render(template) == "Formel 1: Großer Preis von MexikoQualifying"


def test_a_text_literal_in_an_expression_is_capped_at_300_characters() -> None:
    compile_template("{{ '" + "a" * 300 + "' }}")
    err = _reject("{{ '" + "a" * 301 + "' }}")
    assert err.reason == INVALID_TEMPLATE
    assert "300" in err.detail
    assert _reject("{% if title == '" + "a" * 301 + "' %}x{% endif %}").reason == INVALID_TEMPLATE


def test_long_literal_text_outside_braces_is_not_affected() -> None:
    assert _render("a" * 1000 + "{{ title | first }}", title="x") == "a" * 1000 + "x"


def _nested_ifs(depth: int) -> str:
    return "{% if title %}" * depth + "x" + "{% endif %}" * depth


HOSTILE: dict[str, tuple[str, int]] = {
    "chain-143": (_chain(143), MAX_TITLE_TEMPLATE_LENGTH),
    "chain-286": (_chain(286), MAX_TITLE_TEMPLATE_LENGTH),
    "chain-1000": (_chain(1000), 10000),
    "nested-if-130": (_nested_ifs(130), MAX_DESCRIPTION_TEMPLATE_LENGTH),
    "nested-if-1000": (_nested_ifs(1000), 30000),
    "parentheses-500": ("{{ " + "(" * 500 + "title" + ")" * 500 + " }}", MAX_DESCRIPTION_TEMPLATE_LENGTH),
    "nested-list-500": ("{{ " + "[" * 500 + "title" + "]" * 500 + " }}", MAX_DESCRIPTION_TEMPLATE_LENGTH),
    "nested-neg-1000": ("{{ " + "-" * 1000 + "1 }}", MAX_DESCRIPTION_TEMPLATE_LENGTH),
    "nested-not-1000": ("{{ " + "not " * 1000 + "title }}", MAX_DESCRIPTION_TEMPLATE_LENGTH),
    "nested-getitem": ("{{ title" + "[0]" * 1000 + " }}", MAX_DESCRIPTION_TEMPLATE_LENGTH),
    "nested-cond-expr": ("{{ " + "1 if title else " * 400 + "2 }}", MAX_DESCRIPTION_TEMPLATE_LENGTH),
    "huge-power": ("{{ (99 ** 99999999) | string | length }}", MAX_TITLE_TEMPLATE_LENGTH),
    "modulo-format": ("{{ '%s' % title }}", MAX_TITLE_TEMPLATE_LENGTH),
    "range": ("{{ range(10 ** 9) | list | length }}", MAX_TITLE_TEMPLATE_LENGTH),
    "method-call": ("{{ title.upper() }}", MAX_TITLE_TEMPLATE_LENGTH),
    "self-reference": ("{{ self }}", MAX_TITLE_TEMPLATE_LENGTH),
    "star-arguments": ("{{ categories | join(*categories) }}", MAX_TITLE_TEMPLATE_LENGTH),
    "long-literal": ("{{ '" + "a" * 1500 + "' }}", MAX_TITLE_TEMPLATE_LENGTH),
    "unclosed-nesting": ("{{ " + "(" * 900, MAX_TITLE_TEMPLATE_LENGTH),
}


@pytest.mark.parametrize("name", sorted(HOSTILE))
def test_hostile_templates_are_rejected_quickly(name: str) -> None:
    text, max_length = HOSTILE[name]
    started = time.perf_counter()
    with contextlib.suppress(TemplateError):  # the only exception compile_template may raise
        compile_template(text, max_length=max_length)
    assert time.perf_counter() - started < 1


@pytest.mark.parametrize("name", ["nested-if-130", "parentheses-500", "chain-143"])
def test_hostile_templates_that_must_not_compile(name: str) -> None:
    text, max_length = HOSTILE[name]
    with pytest.raises(TemplateError) as err:
        compile_template(text, max_length=max_length)
    assert err.value.reason in {INVALID_TEMPLATE, UNSUPPORTED_SYNTAX}


# --- replace and regex_replace refuse to amplify (T-05-11) ------------------------------------------------------------


def _replace(*args: Any) -> str:
    return ENV.filters["replace"](*args)


def test_replace_behaves_like_the_standard_filter_for_ordinary_text() -> None:
    assert _render("{{ title | replace('a', 'b') }}", title="banana") == "bbnbnb"
    assert _render("{{ title | replace('a', 'b', 2) }}", title="banana") == "bbnbna"
    assert _render("{{ title | replace('a', 'b', count=1) }}", title="banana") == "bbnana"
    assert _render("{{ categories[9] | replace('a', 'b') }}") == ""
    assert _replace(None, "a", "b") == ""
    assert _replace(jinja2.Undefined(), "a", "b") == ""
    assert _replace(12, "1", "x") == "x2"
    assert _replace("abc", "b", None) == "ac"


def test_replace_is_the_guarded_variant_not_the_standard_one() -> None:
    assert "replace" in CUSTOM_FILTERS
    assert ENV.filters["replace"] is CUSTOM_FILTERS["replace"]


def test_an_oversized_replace_result_is_a_runtime_error() -> None:
    assert len(_replace("a" * 100, "a", "b" * 400)) == 40000  # below the limit
    with pytest.raises(ValueError, match="50000"):
        _replace("a" * 5000, "a", "b" * 300)
    with pytest.raises(ValueError, match="50000"):
        _replace("a" * 50001, "x", "y")  # the result, not the growth, is bounded


def test_an_oversized_regex_replace_result_is_a_runtime_error() -> None:
    with pytest.raises(ValueError, match="50000"):
        regex_replace("a" * 5000, "a", "b" * 300)
    assert regex_replace("a" * 100, "a", "b" * 400) == "b" * 40000


def test_a_compounding_chain_of_replace_calls_stops_at_the_first_oversized_step() -> None:
    template = compile_template(
        "{{ title | replace('a', '" + "b" * 300 + "') | replace('b', '" + "c" * 300 + "') | replace('c', 'd') }}"
    )
    started = time.perf_counter()
    with pytest.raises(ValueError, match="50000"):
        template.render(**{**VALUES, "title": "a" * 5000})
    assert time.perf_counter() - started < 1


# --- The sandbox (T-05-01) ------------------------------------------------------------------------------------------


def test_unsafe_attributes_render_empty() -> None:
    assert _render("{{ title.__class__ }}") == ""
    assert _render("{{ title.__class__.__mro__ }}") == ""
    assert _render("{{ categories.__class__.__base__ }}") == ""
    assert _render("{% set a = title %}{{ a.__class__ }}") == ""


def test_the_environment_is_a_sandbox_without_globals() -> None:
    assert isinstance(ENV, SandboxedEnvironment)
    assert isinstance(ENV, jinja2.sandbox.ImmutableSandboxedEnvironment)
    assert ENV.globals == {}


def test_filters_and_tests_are_pruned_to_the_allow_lists() -> None:
    assert set(ENV.filters) == template_engine.STANDARD_FILTERS | set(CUSTOM_FILTERS)
    assert set(ENV.tests) == template_engine.STANDARD_TESTS
    assert "regex_replace" in CUSTOM_FILTERS
    assert not {"center", "format", "attr", "safe", "tojson", "indent", "e"} & set(ENV.filters)


# --- The contract other modules rely on -----------------------------------------------------------------------------


def test_error_reasons_are_the_six_flow_keys_in_order() -> None:
    assert TEMPLATE_ERROR_REASONS == (
        INVALID_TEMPLATE,
        UNKNOWN_PLACEHOLDER,
        UNSUPPORTED_SYNTAX,
        UNKNOWN_FILTER,
        LEGACY_PLACEHOLDER,
        TEMPLATE_RUNTIME_ERROR,
    )
    assert len(set(TEMPLATE_ERROR_REASONS)) == 6
    for reason in TEMPLATE_ERROR_REASONS:
        assert isinstance(reason, str)
        assert reason == reason.lower()
    assert TEMPLATE_RUNTIME_ERROR == "template_runtime_error"
    assert UNSUPPORTED_SYNTAX == "unsupported_syntax"


def test_template_error_carries_reason_and_detail() -> None:
    err = TemplateError("invalid_template", "line 3: oops")
    assert isinstance(err, ValueError)
    assert (err.reason, err.detail) == ("invalid_template", "line 3: oops")
    assert str(err) == "invalid_template: line 3: oops"


def test_variables_and_caps() -> None:
    assert VARIABLE_ORDER == (
        "channel",
        "channel_id",
        "title",
        "titles",
        "subtitle",
        "subtitles",
        "episode",
        "category",
        "categories",
        "description",
        "start",
        "end",
    )
    assert frozenset(VARIABLE_ORDER) == VARIABLES
    assert MAX_TITLE_TEMPLATE_LENGTH == 2000
    assert MAX_DESCRIPTION_TEMPLATE_LENGTH == 5000
    assert set(VALUES) == set(VARIABLES)  # the fixture mirrors what template_values builds
