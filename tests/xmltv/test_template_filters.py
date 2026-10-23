"""The custom template filters of D-06 and the D-07 recipes, rendered through the real EventTemplates facade."""

from datetime import UTC, datetime, timedelta, tzinfo

import pytest

from custom_components.xmltv_calendar.xmltv.model import Channel, Programme
from custom_components.xmltv_calendar.xmltv.render import EventTemplates, to_event_fields
from custom_components.xmltv_calendar.xmltv.settings import KEY_DESCRIPTION_TEMPLATE, KEY_TITLE_TEMPLATE

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
    assert _title("{{ categories[3] | first_line }}|{{ categories[3] | lines | length }}", programme) == "|0"
