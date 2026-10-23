"""The README's template recipes are rendered by the real engine, so the documentation cannot drift from the code."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from custom_components.xmltv_calendar.xmltv.model import Channel, Programme
from custom_components.xmltv_calendar.xmltv.render import EventTemplates, to_event_fields
from custom_components.xmltv_calendar.xmltv.settings import (
    KEY_CHANNELS,
    KEY_DESCRIPTION_TEMPLATE,
    KEY_TITLE_TEMPLATE,
)
from custom_components.xmltv_calendar.xmltv.template_engine import (
    ENV,
    MAX_DESCRIPTION_TEMPLATE_LENGTH,
    MAX_FILTER_CHAIN,
    MAX_LITERAL_LENGTH,
    MAX_RESULT_CHARS,
    MAX_TITLE_TEMPLATE_LENGTH,
    VARIABLE_ORDER,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
UTC_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
  <programme channel="daserste.de" start="20261013100000 +0000" stop="20261013103000 +0000">
    <title>Tagesschau</title>
  </programme>
</tv>
"""
NOW = "2026-10-13T06:00:00+00:00"
# Zone of the documented local-time recipe: UTC plus two hours, like Europe/Berlin in October
CEST = timezone(timedelta(hours=2))
CHANNEL = Channel(id="daserste.de", display_name="Das Erste")


@dataclass(frozen=True)
class Case:
    """One input programme of a recipe and the text the README documents for it."""

    expected: str
    title: str = "Tagesschau"
    subtitle: str = ""
    description: str | None = None


@dataclass(frozen=True)
class Recipe:
    """A template shown in the README, which kind of template it is, and its documented results."""

    name: str
    kind: str  # "title" or "description"
    template: str
    cases: tuple[Case, ...]


FORMULA_ONE = "{{ channel }}: {{ title | regex_replace('^Formel ?1:? ?', '') }}"

FIRST_LINE_SUBTITLE = "{{ title }}{% if description | first_line %} – {{ description | first_line }}{% endif %}"
CONDITIONAL_SUBTITLE = "{% set sub = subtitle | trim %}{{ title }}{% if sub %} ({{ sub }}){% endif %}"
LOCAL_START = "Starts {{ start | time('%H:%M') }} on {{ channel }}"

RECIPES = (
    Recipe(
        name="formula-one-prefix",
        kind="title",
        template=FORMULA_ONE,
        cases=(Case(title="Formel 1: Großer Preis von Mexiko", expected="Das Erste: Großer Preis von Mexiko"),),
    ),
    Recipe(
        name="first-description-line-as-subtitle",
        kind="title",
        template=FIRST_LINE_SUBTITLE,
        cases=(
            Case(title="Formel 1", description="Qualifying\nPractice and more", expected="Formel 1 – Qualifying"),
            Case(title="Formel 1", description=None, expected="Formel 1"),
        ),
    ),
    Recipe(
        name="conditional-subtitle",
        kind="title",
        template=CONDITIONAL_SUBTITLE,
        cases=(
            Case(title="Tatort", subtitle="Der Fall", expected="Tatort (Der Fall)"),
            Case(title="Tagesschau", expected="Tagesschau"),
        ),
    ),
    Recipe(
        name="local-start-time",
        kind="description",
        template=LOCAL_START,
        cases=(Case(expected="Starts 12:00 on Das Erste"),),
    ),
)


def _programme(case: Case) -> Programme:
    start = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)
    return Programme(
        channel_id=CHANNEL.id,
        start=start,
        stop=start + timedelta(minutes=30),
        titles=(case.title,),
        sub_titles=(case.subtitle,) if case.subtitle else (),
        description=case.description,
        categories=(),
        episode=None,
    )


def _rendered(recipe: Recipe, case: Case) -> str | None:
    key = KEY_TITLE_TEMPLATE if recipe.kind == "title" else KEY_DESCRIPTION_TEMPLATE
    templates = EventTemplates.from_mapping({key: recipe.template})
    fields = to_event_fields(_programme(case), CHANNEL, templates, tz=CEST)
    return fields["summary"] if recipe.kind == "title" else fields["description"]


def test_recipe_is_documented_verbatim() -> None:
    missing = [recipe.name for recipe in RECIPES if recipe.template not in README]
    assert missing == []
    stale = [case.expected for recipe in RECIPES for case in recipe.cases if case.expected not in README]
    assert stale == []


@pytest.mark.parametrize(
    ("recipe", "case"),
    [pytest.param(recipe, case, id=f"{recipe.name}-{case.expected}") for recipe in RECIPES for case in recipe.cases],
)
def test_recipe_renders_as_documented(recipe: Recipe, case: Case) -> None:
    assert _rendered(recipe, case) == case.expected


def _subsection(heading: str) -> str:
    """Return the text of the README subsection `#### heading`, or the empty string when it does not exist."""
    match = re.search(rf"^#### {re.escape(heading)}\n(.*?)(?=^#{{2,4}} |\Z)", README, re.DOTALL | re.MULTILINE)
    return match[1] if match else ""


def test_every_registered_filter_is_documented() -> None:
    documented = _subsection("Filters")
    assert [name for name in sorted(ENV.filters) if f"`{name}`" not in documented] == []


def test_every_variable_is_documented() -> None:
    documented = _subsection("Variables")
    assert [name for name in VARIABLE_ORDER if f"`{name}`" not in documented] == []


def test_limits_are_documented() -> None:
    limits = {
        MAX_TITLE_TEMPLATE_LENGTH,
        MAX_DESCRIPTION_TEMPLATE_LENGTH,
        MAX_FILTER_CHAIN,
        MAX_LITERAL_LENGTH,
        MAX_RESULT_CHARS,
    }
    documented = _subsection("Limits")
    assert [str(number) for number in sorted(limits) if str(number) not in documented] == []


async def _events(hass: HomeAssistant, entity_id: str) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    return [event["summary"] for event in await _events(hass, entity_id)]


async def test_formula_one_recipe_end_to_end(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    """The documented recipe, stored as a calendar template, shows the documented title in calendar.get_events."""
    freezer.move_to(NOW)
    await setup_xmltv(FEED, calendars=(("Erste", {KEY_CHANNELS: ["daserste.de"], KEY_TITLE_TEMPLATE: FORMULA_ONE}),))

    assert await _summaries(hass, "calendar.erste") == [
        "Das Erste: Großer Preis von Mexiko",
        "Das Erste: Tagesschau",
    ]


async def test_local_start_time_recipe_end_to_end(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    berlin_tz: None,
) -> None:
    """A UTC feed under Europe/Berlin shows the Berlin wall time through the documented description recipe."""
    freezer.move_to(NOW)
    await setup_xmltv(UTC_FEED, calendars=(("Erste", {KEY_DESCRIPTION_TEMPLATE: LOCAL_START}),))

    (event,) = await _events(hass, "calendar.erste")
    assert event["description"] == "Starts 12:00 on Das Erste"
