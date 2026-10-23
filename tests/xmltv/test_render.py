"""Event rendering: stable UIDs (EVT-06), title templates (EVT-03) and descriptions (EVT-04)."""

import dataclasses
import io
import logging
import zlib
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from custom_components.xmltv_calendar.xmltv import render
from custom_components.xmltv_calendar.xmltv.model import Channel, Programme
from custom_components.xmltv_calendar.xmltv.parser import parse
from custom_components.xmltv_calendar.xmltv.render import (
    DEFAULT_TEMPLATES,
    INVALID_TEMPLATE,
    LEGACY_PLACEHOLDER,
    MAX_DESCRIPTION_TEMPLATE_LENGTH,
    MAX_TITLE_TEMPLATE_LENGTH,
    TEMPLATE_RUNTIME_ERROR,
    UNKNOWN_PLACEHOLDER,
    VARIABLE_ORDER,
    EventTemplates,
    TemplateError,
    template_values,
    to_event_fields,
    validate_template,
)
from custom_components.xmltv_calendar.xmltv.settings import (
    DEFAULT_TITLE_TEMPLATE,
    KEY_CHANNELS,
    KEY_DESCRIPTION_TEMPLATE,
    KEY_INCLUDE,
    KEY_TITLE_TEMPLATE,
    LEGACY_DEFAULT_TITLE_TEMPLATE,
)

CEST = timezone(timedelta(hours=2))
CHANNEL = Channel(id="daserste.de", display_name="Das Erste")

PROGRAMMES = (
    (
        '<programme channel="daserste.de" start="20261013120000 +0200" stop="20261013121500 +0200">'
        "<title>Tagesschau</title></programme>"
    ),
    '<programme channel="daserste.de" start="20261013121500 +0200"><title>Mittagsmagazin</title></programme>',
    '<programme channel="zdf.de" start="20261013120000 +0200"><title>heute</title></programme>',
)


def _feed(programmes: tuple[str, ...]) -> bytes:
    body = "".join(programmes)
    return f'<?xml version="1.0" encoding="UTF-8"?><tv>{body}</tv>'.encode()


def _uids(feed: bytes) -> dict[tuple[str, str], str | None]:
    epg = parse(io.BytesIO(feed), yield_every=0)
    return {(p.channel_id, p.title): to_event_fields(p, None)["uid"] for p in epg.programmes}


def _programme(title: str, start: datetime) -> Programme:
    return Programme(
        channel_id="daserste.de",
        start=start,
        stop=start + timedelta(minutes=15),
        titles=(title,),
        sub_titles=(),
        description=None,
        categories=(),
        episode=None,
    )


def test_uid_format_and_stability() -> None:
    programme = _programme("Tagesschau", datetime(2026, 10, 13, 12, tzinfo=CEST))
    crc = zlib.crc32(b"Tagesschau")
    assert to_event_fields(programme, CHANNEL)["uid"] == f"daserste.de-20261013T100000Z-{crc:08x}"

    # Two parses of the same bytes, and the same programmes in reversed file order, give identical UIDs
    first = _uids(_feed(PROGRAMMES))
    assert all(isinstance(uid, str) for uid in first.values())
    assert _uids(_feed(PROGRAMMES)) == first
    assert _uids(_feed(PROGRAMMES[::-1])) == first


def test_uid_differs_for_different_titles() -> None:
    start = datetime(2026, 10, 13, 10, tzinfo=UTC)
    uid_a = to_event_fields(_programme("Tagesschau", start), CHANNEL)["uid"]
    uid_b = to_event_fields(_programme("Wetter", start), CHANNEL)["uid"]
    assert uid_a is not None
    assert uid_b is not None
    assert uid_a != uid_b


def test_summary_and_location_unchanged() -> None:
    programme = _programme("Tagesschau", datetime(2026, 10, 13, 10, tzinfo=UTC))
    fields = to_event_fields(programme, CHANNEL)
    assert fields["summary"] == "Das Erste: Tagesschau"
    assert fields["location"] == "Das Erste"
    assert to_event_fields(programme, None)["location"] == "daserste.de"


# --- Templates (EVT-03, D-01, D-05, D-07, D-09, D-11) --------------------------------------------------------------

BASIC = Path(__file__).parent.parent / "fixtures" / "basic.xml"
START = datetime(2026, 10, 13, 18, tzinfo=UTC)

R1 = Programme(
    channel_id="daserste.de",
    start=START,
    stop=START + timedelta(minutes=90),
    titles=("Tatort", "Tatort (Wh.)"),
    sub_titles=("Der Fall", "Teil 2"),
    description="Kommissarin ermittelt.",
    categories=("Krimi", "Reihe"),
    episode="1.4.",
)
R2 = _programme("Tagesschau", START)
R3 = Programme(
    channel_id="x.de",
    start=START,
    stop=START + timedelta(minutes=15),
    titles=("Nachrichten",),
    sub_titles=(),
    description=None,
    categories=(),
    episode=None,
)
CHANNELS = {"daserste.de": CHANNEL}


def _title(template: str, programme: Programme, *, tz: timezone | None = None) -> str:
    templates = EventTemplates.from_mapping({KEY_TITLE_TEMPLATE: template})
    return to_event_fields(programme, CHANNELS.get(programme.channel_id), templates, tz=tz)["summary"]


@pytest.mark.parametrize(
    ("template", "programme", "expected"),
    [
        ("{{ channel }}: {{ title }}", R1, "Das Erste: Tatort"),
        ("{{ channel }}: {{ title }}", R3, "x.de: Nachrichten"),
        ("{{ title }} – {{ subtitle }}", R1, "Tatort – Der Fall"),
        ("{{ title }} – {{ subtitle }}", R2, "Tagesschau"),
        ("{{ title }} ({{ episode }})", R1, "Tatort (1.4.)"),
        ("{{ category }}: {{ title }}", R2, "Tagesschau"),
        ("{{ category }}: {{ title }}", R1, "Krimi, Reihe: Tatort"),
        ("{{ channel_id }} | {{ title }}", R1, "daserste.de | Tatort"),
        ("  {{ title }}   {{ subtitle }}  ", R1, "Tatort Der Fall"),
        ("{{ subtitle }}", R2, "Tagesschau"),
        ("{{ '{' ~ title ~ '}' }}", R1, "{Tatort}"),
        ("{{ titles | join(' / ') }}", R1, "Tatort / Tatort (Wh.)"),
        ("{{ categories[0] }}", R1, "Krimi"),
        ("{{ categories[0] }}: {{ title }}", R2, "Tagesschau"),
        ("{% if subtitle %}{{ subtitle }}{% else %}{{ title }}{% endif %}", R1, "Der Fall"),
        ("{% if subtitle %}{{ subtitle }}{% else %}{{ title }}{% endif %}", R2, "Tagesschau"),
        ("{{ title }}\n{{ subtitle }}", R1, "Tatort Der Fall"),
    ],
)
def test_title_rendering(template: str, programme: Programme, expected: str) -> None:
    assert _title(template, programme) == expected


def test_description_is_available_in_a_title_template() -> None:
    # D-07: a title template may use the description
    assert _title("{{ description }}", R1) == "Kommissarin ermittelt."
    assert _title("{{ title }}: {{ description }}", R2) == "Tagesschau"


def test_title_whitespace_control_works_on_top_of_the_cleanup() -> None:
    template = "{{ title }}  {%- if subtitle %} / {{ subtitle }}{%- endif %}"
    assert _title(template, R1) == "Tatort / Der Fall"
    assert _title(template, R2) == "Tagesschau"


def test_feed_text_is_data_never_template_source() -> None:
    # T-05-04: feed values are only ever variable values, Jinja never re-renders them
    programme = _programme("{{ 7 * 7 }} {% if 1 %}x{% endif %} {{ title }}", START)
    assert _title("{{ title }}", programme) == "{{ 7 * 7 }} {% if 1 %}x{% endif %} {{ title }}"
    assert to_event_fields(programme, CHANNEL)["summary"] == "Das Erste: {{ 7 * 7 }} {% if 1 %}x{% endif %} {{ title }}"


def test_uid_ignores_templates() -> None:
    templated = EventTemplates.from_mapping({KEY_TITLE_TEMPLATE: "{{ title }} – {{ subtitle }}"})
    assert to_event_fields(R1, CHANNEL, templated)["uid"] == to_event_fields(R1, CHANNEL, DEFAULT_TEMPLATES)["uid"]


def test_default_templates_reproduce_phase1_summary() -> None:
    # Assumption-delta invariant: the default template is the Phase 1 hard-coded summary
    epg = parse(io.BytesIO(BASIC.read_bytes()), yield_every=0)
    cases = [(R1, CHANNEL), (R2, CHANNEL)] + [(p, epg.channels[p.channel_id]) for p in epg.programmes]
    for programme, channel in cases:
        fields = to_event_fields(programme, channel)
        assert fields["summary"] == f"{channel.display_name}: {programme.title}"
        assert fields == to_event_fields(programme, channel, DEFAULT_TEMPLATES)


# --- Variables (D-05) ----------------------------------------------------------------------------------------------


def test_template_values_are_flat_and_typed() -> None:
    values = template_values(R1, CHANNEL)

    assert set(values) == set(VARIABLE_ORDER)
    assert values["channel"] == "Das Erste"
    assert values["channel_id"] == "daserste.de"
    assert values["title"] == "Tatort"
    assert values["titles"] == ["Tatort", "Tatort (Wh.)"]
    assert values["subtitle"] == "Der Fall"
    assert values["subtitles"] == ["Der Fall", "Teil 2"]
    assert values["episode"] == "1.4."
    assert values["category"] == "Krimi, Reihe"
    assert values["categories"] == ["Krimi", "Reihe"]
    assert values["description"] == "Kommissarin ermittelt."
    assert values["start"] == R1.start
    assert values["end"] == R1.stop


def test_template_values_of_a_sparse_programme_are_empty_not_missing() -> None:
    values = template_values(R3, None)

    assert set(values) == set(VARIABLE_ORDER)
    assert values["channel"] == "x.de"
    assert values["subtitle"] == ""
    assert values["subtitles"] == []
    assert values["episode"] == ""
    assert values["category"] == ""
    assert values["categories"] == []
    assert values["description"] == ""


def test_start_and_end_stay_as_parsed_without_a_zone_and_convert_with_one() -> None:
    programme = _programme("Tagesschau", datetime(2026, 10, 13, 18, tzinfo=UTC))

    assert _title("{{ start }}", programme) == "2026-10-13 18:00:00+00:00"
    assert _title("{{ end }}", programme) == "2026-10-13 18:15:00+00:00"
    assert _title("{{ start }}", programme, tz=CEST) == "2026-10-13 20:00:00+02:00"
    assert _title("{{ end }}", programme, tz=CEST) == "2026-10-13 20:15:00+02:00"
    assert template_values(programme, CHANNEL, tz=CEST)["start"] == programme.start  # same instant
    assert template_values(programme, CHANNEL, tz=CEST)["start"].utcoffset() == timedelta(hours=2)


# --- EventTemplates: equality, stored templates, fallbacks (D-03, D-08, D-11) ---------------------------------------


def test_equality_compares_template_sources_only() -> None:
    data = {KEY_TITLE_TEMPLATE: "{{ title }}", KEY_DESCRIPTION_TEMPLATE: "{{ description }}"}

    assert EventTemplates.from_mapping(data) == EventTemplates.from_mapping(dict(data))
    assert EventTemplates.from_mapping(data) != EventTemplates.from_mapping(
        {**data, KEY_TITLE_TEMPLATE: "{{ channel }}"}
    )
    assert EventTemplates.from_mapping(data) != EventTemplates.from_mapping({KEY_TITLE_TEMPLATE: "{{ title }}"})
    # A filter-only edit never looks like a template change (matcher.async_apply_subentry compares these)
    assert EventTemplates.from_mapping(
        {**data, KEY_INCLUDE: "formel", KEY_CHANNELS: ["x"]}
    ) == EventTemplates.from_mapping(data)
    assert EventTemplates.from_mapping({}) == DEFAULT_TEMPLATES


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.levelno >= logging.WARNING]


def test_from_mapping_without_a_name_logs_nothing(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        templates = EventTemplates.from_mapping({KEY_TITLE_TEMPLATE: "{title}", KEY_DESCRIPTION_TEMPLATE: "{{ foo }}"})

    assert _warnings(caplog) == []
    assert to_event_fields(R1, CHANNEL, templates)["summary"] == "Das Erste: Tatort"


def test_stored_legacy_template_falls_back_with_one_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        templates = EventTemplates.from_mapping({KEY_TITLE_TEMPLATE: "{title} - {subtitle}"}, "Abend")

    (message,) = _warnings(caplog)
    assert "Abend" in message
    assert "title" in message
    assert LEGACY_PLACEHOLDER in message
    assert "{subtitle}" not in message  # the template text never reaches the log
    assert to_event_fields(R1, CHANNEL, templates)["summary"] == "Das Erste: Tatort"
    assert templates == DEFAULT_TEMPLATES  # the effective source is the default


def test_stored_legacy_description_falls_back_to_the_default_description(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        templates = EventTemplates.from_mapping({KEY_DESCRIPTION_TEMPLATE: "{description}"}, "Abend")

    (message,) = _warnings(caplog)
    assert "description" in message
    assert LEGACY_PLACEHOLDER in message
    assert to_event_fields(R1, CHANNEL, templates)["description"] == render.default_description(R1)


def test_exact_legacy_default_logs_nothing(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        templates = EventTemplates.from_mapping({KEY_TITLE_TEMPLATE: LEGACY_DEFAULT_TITLE_TEMPLATE}, "Abend")

    assert _warnings(caplog) == []
    assert templates == DEFAULT_TEMPLATES
    assert to_event_fields(R1, CHANNEL, templates)["summary"] == "Das Erste: Tatort"


def test_stored_uncompilable_template_falls_back_with_one_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        templates = EventTemplates.from_mapping(
            {KEY_TITLE_TEMPLATE: "{{ title.__class__ | nope }}", KEY_DESCRIPTION_TEMPLATE: "{{ foo"}, "Abend"
        )

    messages = _warnings(caplog)
    assert len(messages) == 2  # one per unusable stored template, each naming its kind
    assert all("Abend" in message for message in messages)
    assert all("__class__" not in message and "nope" not in message and "foo" not in message for message in messages)
    assert to_event_fields(R1, CHANNEL, templates)["summary"] == "Das Erste: Tatort"
    assert to_event_fields(R1, CHANNEL, templates)["description"] == render.default_description(R1)


def test_template_that_raises_at_render_falls_back_with_one_warning(caplog: pytest.LogCaptureFixture) -> None:
    data = {KEY_TITLE_TEMPLATE: "{{ 1 / 0 }}", KEY_DESCRIPTION_TEMPLATE: "{{ 1 / 0 }}"}
    templates = EventTemplates.from_mapping(data, "Abend")
    programmes = (R1, R2, R3, _programme("Streng geheimer Titel", START))

    with caplog.at_level(logging.DEBUG):
        results = [
            to_event_fields(programme, CHANNELS.get(programme.channel_id), templates) for programme in programmes
        ]

    assert [fields["summary"] for fields in results] == [programme.title for programme in programmes]
    assert [fields["description"] for fields in results] == [render.default_description(p) for p in programmes]
    (message,) = _warnings(caplog)  # one WARNING per calendar across many renders and both templates
    assert "Abend" in message
    assert "ZeroDivisionError" in message
    assert "Streng geheimer Titel" not in message
    assert "1 / 0" not in message
    later = [
        record
        for record in caplog.records
        if record.levelno < logging.WARNING and "ZeroDivisionError" in record.getMessage()
    ]
    assert later  # later failures are logged at DEBUG


def test_render_failure_without_a_name_is_quiet(caplog: pytest.LogCaptureFixture) -> None:
    templates = EventTemplates.from_mapping({KEY_TITLE_TEMPLATE: "{{ 1 / 0 }}"})

    with caplog.at_level(logging.DEBUG):
        assert to_event_fields(R1, CHANNEL, templates)["summary"] == "Tatort"

    assert _warnings(caplog) == []


def test_empty_rendered_title_falls_back_to_the_programme_title() -> None:
    # D-11: CalendarEvent needs a summary
    assert _title("{{ subtitle }}", R2) == "Tagesschau"
    assert _title("{{ '' }}", R1) == "Tatort"
    assert _title("{{ ' - ' }}", R1) == "Tatort"


# --- validate_template (flow facade) -------------------------------------------------------------------------------


def test_validate_template_uses_the_caps_of_the_template_kind() -> None:
    validate_template("a" * MAX_TITLE_TEMPLATE_LENGTH)
    validate_template("a" * MAX_DESCRIPTION_TEMPLATE_LENGTH, description=True)

    with pytest.raises(TemplateError) as title_err:
        validate_template("a" * (MAX_TITLE_TEMPLATE_LENGTH + 1))
    assert title_err.value.reason == INVALID_TEMPLATE
    with pytest.raises(TemplateError) as description_err:
        validate_template("a" * (MAX_DESCRIPTION_TEMPLATE_LENGTH + 1), description=True)
    assert description_err.value.reason == INVALID_TEMPLATE
    # The description cap is the longer one
    validate_template("a" * (MAX_TITLE_TEMPLATE_LENGTH + 1), description=True)


@pytest.mark.parametrize(
    ("template", "reason", "detail"),
    [
        ("{{ foo }}", UNKNOWN_PLACEHOLDER, "foo"),
        ("{legacy} {title}", LEGACY_PLACEHOLDER, "{title}"),
        ("{{ title", INVALID_TEMPLATE, None),
    ],
)
def test_validate_template_raises_the_engine_reasons(template: str, reason: str, detail: str | None) -> None:
    with pytest.raises(TemplateError) as err:
        validate_template(template)
    assert err.value.reason == reason
    if detail is not None:
        assert err.value.detail == detail


def test_default_title_template_validates() -> None:
    validate_template(DEFAULT_TITLE_TEMPLATE)


def test_validate_template_rejects_a_zero_division_at_render() -> None:
    with pytest.raises(TemplateError) as err:
        validate_template("{{ 1 / 0 }}")
    assert err.value.reason == TEMPLATE_RUNTIME_ERROR
    assert err.value.detail.startswith("ZeroDivisionError")


def test_validate_template_rejects_a_type_error_at_render() -> None:
    with pytest.raises(TemplateError) as err:
        validate_template("{{ title | truncate('a') }}")
    assert err.value.reason == TEMPLATE_RUNTIME_ERROR
    assert "Error" in err.value.detail


def test_runtime_error_detail_is_cut_to_200_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Raising:
        def render(self, **_values: object) -> str:
            raise ValueError("x" * 500)

    monkeypatch.setattr(render, "compile_template", lambda *_args, **_kwargs: _Raising())

    with pytest.raises(TemplateError) as err:
        validate_template("anything")
    assert err.value.reason == TEMPLATE_RUNTIME_ERROR
    assert err.value.detail.startswith("ValueError: ")
    assert len(err.value.detail) == 200


@pytest.mark.parametrize(
    "template",
    [
        "{{ subtitles[0] | upper }}",
        "{{ categories[0] }}",
        "{{ description | trim }}",
        "{{ episode }}",
        "{{ '' }}",
    ],
)
def test_empty_optional_fields_never_fail_the_trial_render(template: str) -> None:
    validate_template(template)
    validate_template(template, description=True)


def test_description_length_cap_still_applies_before_the_trial_render() -> None:
    validate_template("a" * 3000, description=True)
    with pytest.raises(TemplateError) as err:
        validate_template("a" * 3000)
    assert err.value.reason == INVALID_TEMPLATE


# --- Descriptions (EVT-04, D-23) -----------------------------------------------------------------------------------


def _with(**changes: object) -> Programme:
    return dataclasses.replace(R2, **changes)


def _description(programme: Programme, data: dict[str, object] | None = None) -> str | None:
    templates = EventTemplates.from_mapping(data) if data is not None else DEFAULT_TEMPLATES
    return to_event_fields(programme, CHANNEL, templates)["description"]


def test_default_description_layout() -> None:
    assert _description(R1) == "Der Fall\nEpisode: 1.4.\nCategories: Krimi, Reihe\n\nKommissarin ermittelt."


@pytest.mark.parametrize(
    ("programme", "expected"),
    [
        (R2, None),
        (_with(description="Nur Text."), "Nur Text."),
        (_with(categories=("A",)), "Categories: A"),
        (_with(episode="S01E04"), "Episode: S01E04"),
        (_with(sub_titles=("Teil 1",), description="Text."), "Teil 1\n\nText."),
    ],
)
def test_default_description_drops_empty_lines(programme: Programme, expected: str | None) -> None:
    assert _description(programme) == expected


def test_default_description_helper() -> None:
    assert render.default_description(R1) == _description(R1)
    assert render.default_description(R2) is None


@pytest.mark.parametrize(
    ("template", "programme", "expected"),
    [
        ("{{ description }}\n\n{{ category }}", R1, "Kommissarin ermittelt.\n\nKrimi, Reihe"),
        ("{{ description }}\n\n{{ category }}", R2, None),
        ("- {{ subtitle }}\n- {{ episode }}", R1, "- Der Fall\n- 1.4."),
        ("- {{ subtitle }}\n- {{ episode }}", R2, None),
        (
            "{{ title }}   {{ subtitle }}\n\n\n\n{{ description }}",
            R1,
            "Tatort Der Fall\n\nKommissarin ermittelt.",
        ),
        ("{{ episode }}: {{ description }}", R2, None),
        ("{{ channel }}: {{ title }}", R1, "Das Erste: Tatort"),
        ("{{ categories | join(' · ') }}", R1, "Krimi · Reihe"),
        (
            "{% if episode %}Episode: {{ episode }}\n{% endif %}{{ description }}",
            R1,
            "Episode: 1.4.\nKommissarin ermittelt.",
        ),
    ],
)
def test_description_template(template: str, programme: Programme, expected: str | None) -> None:
    assert _description(programme, {KEY_DESCRIPTION_TEMPLATE: template}) == expected


def test_block_tags_on_their_own_lines_leave_no_blank_line() -> None:
    # trim_blocks and lstrip_blocks keep a block tag on its own line from leaving a blank line (A2)
    template = "{% if episode %}\nEpisode: {{ episode }}\n{% endif %}\n{{ description }}"
    assert _description(R1, {KEY_DESCRIPTION_TEMPLATE: template}) == "Episode: 1.4.\nKommissarin ermittelt."
    assert _description(_with(description="Text."), {KEY_DESCRIPTION_TEMPLATE: template}) == "Text."


def test_description_template_strips_dangling_leading_punctuation() -> None:
    template = {KEY_DESCRIPTION_TEMPLATE: "{{ episode }}: {{ description }}"}
    assert _description(_with(description="Text."), template) == "Text."


def test_empty_description_template_means_the_default_description() -> None:
    assert _description(R1, {KEY_DESCRIPTION_TEMPLATE: "   "}) == render.default_description(R1)
