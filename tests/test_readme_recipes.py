"""The README's template recipes are rendered by the real engine, so the documentation cannot drift from the code."""

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

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
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

RECIPES = (
    Recipe(
        name="formula-one-prefix",
        kind="title",
        template=FORMULA_ONE,
        cases=(Case(title="Formel 1: Großer Preis von Mexiko", expected="Das Erste: Großer Preis von Mexiko"),),
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


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


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
