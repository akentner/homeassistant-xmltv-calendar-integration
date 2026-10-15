"""German translation (de.json) is served by Home Assistant and mirrors en.json (CFG-04, UAT 02 test 1)."""

import json
import logging
import re
import string
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.translation import async_get_translations

import custom_components.xmltv_calendar as integration
from custom_components.xmltv_calendar.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

TRANSLATIONS = Path(integration.__file__).parent / "translations"
EN_JSON = TRANSLATIONS / "en.json"
DE_JSON = TRANSLATIONS / "de.json"

# Same names as Home Assistant core's workday integration
GERMAN_WEEKDAYS = {
    "mon": "Montag",
    "tue": "Dienstag",
    "wed": "Mittwoch",
    "thu": "Donnerstag",
    "fri": "Freitag",
    "sat": "Samstag",
    "sun": "Sonntag",
}

# hassfest's value rules; hassfest skips de.json for custom integrations, so this test enforces them
_SINGLE_QUOTED_PLACEHOLDER = re.compile(r"'\{[^{}]*\}'")
_HTML_TAG = re.compile(r"<[A-Za-z/!]")
_URL = re.compile(r"\b(?:https?|ftps?|mqtts?)://[\w-]+(?:\.[\w-]+)+|\bwww\.[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(node, dict):
        return {prefix: node}
    flat: dict[str, Any] = {}
    for key, value in node.items():
        flat.update(_flatten(value, f"{prefix}.{key}" if prefix else key))
    return flat


def _placeholders(text: str) -> set[str]:
    # The extraction homeassistant.helpers.translation._validate_placeholders uses
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


async def test_home_assistant_serves_german_strings(hass: HomeAssistant, caplog: Any) -> None:
    served = await async_get_translations(hass, "de", "selector", [DOMAIN])
    weekdays = {day: served.get(f"component.{DOMAIN}.selector.weekday.options.{day}") for day in GERMAN_WEEKDAYS}
    assert weekdays == GERMAN_WEEKDAYS

    assert DE_JSON.is_file()
    for section, node in _load(DE_JSON).items():
        served = await async_get_translations(hass, "de", section, [DOMAIN])
        expected = _flatten(node, f"component.{DOMAIN}.{section}")
        assert {key: served.get(key) for key in expected} == expected, section

    errors = [
        record.getMessage()
        for record in caplog.records
        if record.name == "homeassistant.helpers.translation" and record.levelno >= logging.ERROR
    ]
    assert errors == []


def test_de_values_follow_hassfest_rules() -> None:
    assert DE_JSON.is_file()
    violations: dict[str, str] = {}
    for key, value in _flatten(_load(DE_JSON)).items():
        if not isinstance(value, str) or not value:
            violations[key] = "not a non-empty string"
        elif value != value.strip():
            violations[key] = "leading or trailing whitespace"
        elif "[%" in value:
            violations[key] = "[% reference"
        elif _SINGLE_QUOTED_PLACEHOLDER.search(value):
            violations[key] = "single-quoted placeholder"
        elif _HTML_TAG.search(value):
            violations[key] = "HTML tag"
        elif _URL.search(value):
            violations[key] = "URL"
        else:
            try:
                names = _placeholders(value)
            except ValueError as err:
                violations[key] = f"unparsable placeholder: {err}"
            else:
                if not all(name.isidentifier() for name in names):
                    violations[key] = f"placeholder is not an identifier: {sorted(names)}"
    assert violations == {}
